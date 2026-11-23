"""Tenant membership and credential administration.

All writes are serialized per tenant and paired with a PostgreSQL audit event.
The caller supplies an already authenticated principal; authorization is enforced
at the API boundary and ownership invariants are enforced again in this store.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from .identity import digest_api_key


class TenantAdminError(ValueError):
    pass


class TenantAdminUnavailable(RuntimeError):
    pass


class TenantAdminStore:
    def __init__(self, dsn: str, pepper: str, connect_factory: Callable[[], Any] | None = None):
        if not isinstance(dsn, str) or not dsn.strip():
            raise TenantAdminUnavailable("PostgreSQL tenant identity is not configured")
        if not isinstance(pepper, str) or len(pepper) < 32:
            raise TenantAdminUnavailable("OMNIS_API_KEY_PEPPER must contain at least 32 characters")
        self.dsn, self.pepper, self.connect_factory = dsn, pepper, connect_factory

    def _connect(self):
        if self.connect_factory:
            return self.connect_factory()
        try:
            from psycopg.rows import dict_row
            from .postgres_connection import connect_postgres
            return connect_postgres(self.dsn, dict_row, statement_timeout_ms=8000)
        except Exception as exc:
            raise TenantAdminUnavailable("tenant administration storage is unavailable") from exc

    @staticmethod
    def _uuid(value: str) -> str:
        try:
            return str(UUID(str(value)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise TenantAdminError("identifier must be a UUID") from exc

    @staticmethod
    def _lock_tenant(cur, tenant: str) -> None:
        cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant,))
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"omnis.tenant_admin:{tenant}",))
        cur.execute("SELECT status FROM omnis.tenant WHERE tenant_id = %s", (tenant,))
        row = cur.fetchone()
        if not row or row["status"] != "active":
            raise TenantAdminError("tenant is unavailable")

    def list_members(self, tenant_id: str) -> list[dict[str, Any]]:
        tenant = self._uuid(tenant_id)
        with self._connect() as db:
            with db.cursor() as cur:
                cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant,))
                cur.execute(
                    """SELECT p.principal_id, p.email, p.display_name, p.status AS principal_status,
                              m.role, m.status AS membership_status, m.created_at
                       FROM omnis.tenant_membership m
                       JOIN omnis.principal p ON p.principal_id = m.principal_id
                       WHERE m.tenant_id = %s ORDER BY p.email""",
                    (tenant,),
                )
                return list(cur.fetchall())

    def add_member(self, tenant_id: str, email: str, display_name: str, role: str,
                   actor_id: str, audit_log) -> dict[str, Any]:
        tenant, actor = self._uuid(tenant_id), self._uuid(actor_id)
        email = email.strip().lower() if isinstance(email, str) else ""
        display_name = display_name.strip() if isinstance(display_name, str) else ""
        if not 3 <= len(email) <= 320 or email.count("@") != 1 or any(ch.isspace() for ch in email):
            raise TenantAdminError("email address is invalid")
        if not 1 <= len(display_name) <= 160:
            raise TenantAdminError("display_name must contain 1-160 characters")
        if role not in {"owner", "admin", "operator", "analyst", "reader"}:
            raise TenantAdminError("role is invalid")
        with self._connect() as db:
            with db.cursor() as cur:
                self._lock_tenant(cur, tenant)
                cur.execute(
                    """INSERT INTO omnis.principal (email, display_name)
                       VALUES (%s, %s) ON CONFLICT (email) DO NOTHING
                       RETURNING principal_id""",
                    (email, display_name),
                )
                inserted_principal = cur.fetchone()
                if inserted_principal:
                    principal_id = str(inserted_principal["principal_id"])
                else:
                    cur.execute(
                        "SELECT principal_id, status, display_name FROM omnis.principal WHERE email = %s FOR UPDATE",
                        (email,),
                    )
                    principal = cur.fetchone()
                    if principal is None or principal["status"] != "active":
                        raise TenantAdminError("principal is unavailable")
                    principal_id = str(principal["principal_id"])
                    display_name = principal["display_name"]
                cur.execute(
                    """UPDATE omnis.api_credential SET revoked_at = now()
                       WHERE tenant_id = %s AND principal_id = %s AND revoked_at IS NULL
                       RETURNING credential_id""",
                    (tenant, principal_id),
                )
                revoked_credentials = len(cur.fetchall())
                cur.execute(
                    """INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status)
                       VALUES (%s, %s, %s, 'active')
                       ON CONFLICT (tenant_id, principal_id) DO UPDATE
                       SET role = EXCLUDED.role, status = 'active'
                       WHERE omnis.tenant_membership.status = 'suspended'
                       RETURNING principal_id""",
                    (tenant, principal_id, role),
                )
                if cur.fetchone() is None:
                    raise TenantAdminError("principal is already an active member of this tenant")
                audit_log.record_in_transaction(
                    db, "tenant.member.added",
                    {"tenant_id": tenant, "principal_id": principal_id, "role": role,
                     "revoked_credentials": revoked_credentials}, actor=actor,
                )
        return {"tenant_id": tenant, "principal_id": principal_id, "email": email,
                "display_name": display_name, "role": role, "status": "active"}

    def update_member(self, tenant_id: str, principal_id: str, role: str, status: str,
                      actor_id: str, actor_role: str, audit_log) -> dict[str, Any]:
        tenant, member, actor = self._uuid(tenant_id), self._uuid(principal_id), self._uuid(actor_id)
        if role not in {"owner", "admin", "operator", "analyst", "reader"}:
            raise TenantAdminError("role is invalid")
        if status not in {"active", "suspended"}:
            raise TenantAdminError("status is invalid")
        with self._connect() as db:
            with db.cursor() as cur:
                self._lock_tenant(cur, tenant)
                cur.execute(
                    """SELECT role, status FROM omnis.tenant_membership
                       WHERE tenant_id = %s AND principal_id = %s FOR UPDATE""",
                    (tenant, member),
                )
                current = cur.fetchone()
                if not current:
                    raise TenantAdminError("tenant membership not found")
                if current["role"] == "owner" and actor_role != "owner":
                    raise TenantAdminError("only an owner may modify another owner's membership")
                if current["role"] == "owner" and (role != "owner" or status != "active"):
                    cur.execute(
                        """SELECT count(*) AS owners FROM omnis.tenant_membership
                           WHERE tenant_id = %s AND role = 'owner' AND status = 'active'""",
                        (tenant,),
                    )
                    if cur.fetchone()["owners"] <= 1:
                        raise TenantAdminError("cannot demote or suspend the last active tenant owner")
                revoked_credentials = 0
                if status == "suspended" and current["status"] != "suspended":
                    cur.execute(
                        """UPDATE omnis.api_credential SET revoked_at = now()
                           WHERE tenant_id = %s AND principal_id = %s AND revoked_at IS NULL
                           RETURNING credential_id""",
                        (tenant, member),
                    )
                    revoked_credentials = len(cur.fetchall())
                cur.execute(
                    """UPDATE omnis.tenant_membership SET role = %s, status = %s
                       WHERE tenant_id = %s AND principal_id = %s""",
                    (role, status, tenant, member),
                )
                audit_log.record_in_transaction(
                    db, "tenant.member.updated",
                    {"tenant_id": tenant, "principal_id": member,
                     "previous_role": current["role"], "role": role,
                     "previous_status": current["status"], "status": status,
                     "revoked_credentials": revoked_credentials},
                    actor=actor,
                )
        return {"tenant_id": tenant, "principal_id": member, "role": role, "status": status}

    def issue_credential(self, tenant_id: str, principal_id: str, label: str,
                         expires_in_days: int, actor_id: str, actor_role: str, audit_log) -> dict[str, Any]:
        tenant, member, actor = self._uuid(tenant_id), self._uuid(principal_id), self._uuid(actor_id)
        label = label.strip() if isinstance(label, str) else ""
        if not 1 <= len(label) <= 100:
            raise TenantAdminError("label must contain 1-100 characters")
        if isinstance(expires_in_days, bool) or not isinstance(expires_in_days, int) or not 1 <= expires_in_days <= 365:
            raise TenantAdminError("expires_in_days must be between 1 and 365")
        token = "omnis_live_" + secrets.token_urlsafe(36)
        digest = digest_api_key(token, self.pepper)
        with self._connect() as db:
            with db.cursor() as cur:
                self._lock_tenant(cur, tenant)
                cur.execute(
                    """SELECT m.role FROM omnis.tenant_membership m
                       JOIN omnis.principal p ON p.principal_id = m.principal_id
                       WHERE m.tenant_id = %s AND m.principal_id = %s
                         AND m.status = 'active' AND p.status = 'active'""",
                    (tenant, member),
                )
                membership = cur.fetchone()
                if membership is None:
                    raise TenantAdminError("active tenant membership not found")
                if membership["role"] == "owner" and actor_role != "owner":
                    raise TenantAdminError("only an owner may issue credentials for another owner")
                expires = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
                cur.execute(
                    """INSERT INTO omnis.api_credential
                       (tenant_id, principal_id, token_prefix, token_digest, label, expires_at)
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING credential_id, created_at""",
                    (tenant, member, token[:32], digest, label, expires),
                )
                created = cur.fetchone()
                audit_log.record_in_transaction(
                    db, "tenant.credential.issued",
                    {"tenant_id": tenant, "principal_id": member,
                     "credential_id": str(created["credential_id"]), "label": label,
                     "expires_at": expires.isoformat()}, actor=actor,
                )
        return {"credential_id": str(created["credential_id"]), "principal_id": member,
                "label": label, "expires_at": expires.isoformat(), "api_token_once": token}

    def revoke_credential(self, tenant_id: str, credential_id: str, actor_id: str,
                          actor_role: str, audit_log) -> dict[str, Any]:
        tenant, credential, actor = self._uuid(tenant_id), self._uuid(credential_id), self._uuid(actor_id)
        with self._connect() as db:
            with db.cursor() as cur:
                self._lock_tenant(cur, tenant)
                cur.execute(
                    """SELECT c.credential_id, c.principal_id, c.revoked_at, m.role
                       FROM omnis.api_credential c
                       JOIN omnis.tenant_membership m ON m.principal_id = c.principal_id
                       WHERE c.credential_id = %s AND c.tenant_id = %s
                         AND m.tenant_id = c.tenant_id""",
                    (credential, tenant),
                )
                row = cur.fetchone()
                if not row:
                    raise TenantAdminError("credential not found in this tenant")
                if row["role"] == "owner" and actor_role != "owner":
                    raise TenantAdminError("only an owner may revoke another owner's credential")
                if row["revoked_at"] is None:
                    cur.execute(
                        "UPDATE omnis.api_credential SET revoked_at = now() WHERE credential_id = %s",
                        (credential,),
                    )
                    audit_log.record_in_transaction(
                        db, "tenant.credential.revoked",
                        {"tenant_id": tenant, "principal_id": str(row["principal_id"]),
                         "credential_id": credential}, actor=actor,
                    )
        return {"tenant_id": tenant, "credential_id": credential, "revoked": True}
