"""Tenant-aware API-key authentication primitives for OMNIS.

The legacy shared OMNIS_API_TOKEN remains separate. Tenant credentials are
high-entropy, per-principal tokens and are never stored in plaintext.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Callable

_TOKEN_RE = re.compile(r"^omnis_live_[A-Za-z0-9_-]{40,}$")
_ROLE_PERMISSIONS = {
    "owner": frozenset({"identity:read", "tenant:manage", "members:manage", "credentials:manage", "evidence:read", "evidence:write", "governance:execute", "audit:read"}),
    "admin": frozenset({"identity:read", "members:manage", "credentials:manage", "evidence:read", "evidence:write", "governance:execute", "audit:read"}),
    "operator": frozenset({"identity:read", "evidence:read", "evidence:write", "governance:execute"}),
    "analyst": frozenset({"identity:read", "evidence:read", "governance:execute", "audit:read"}),
    "reader": frozenset({"identity:read", "evidence:read"}),
}


class IdentityUnavailable(RuntimeError):
    """Identity storage or required security configuration is unavailable."""


class InvalidCredential(ValueError):
    """The supplied credential is invalid, expired, revoked, or outside its tenant."""


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    principal_id: str
    email: str
    display_name: str
    role: str
    credential_prefix: str

    @property
    def permissions(self) -> frozenset[str]:
        return _ROLE_PERMISSIONS[self.role]

    def allows(self, permission: str) -> bool:
        return permission in self.permissions


def normalize_tenant_id(value: str | None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidCredential("X-OMNIS-Tenant must identify one tenant")
    try:
        return str(uuid.UUID(value.strip()))
    except (ValueError, AttributeError, TypeError) as exc:
        raise InvalidCredential("X-OMNIS-Tenant must be a UUID") from exc


def digest_api_key(token: str, pepper: str) -> str:
    if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token):
        raise InvalidCredential("malformed API credential")
    if not isinstance(pepper, str) or len(pepper) < 32:
        raise IdentityUnavailable("OMNIS_API_KEY_PEPPER must contain at least 32 characters")
    return hmac.new(pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def _connect(dsn: str, connect_factory: Callable[[], Any] | None = None):
    if connect_factory is not None:
        return connect_factory()
    try:
        from psycopg.rows import dict_row
        from .postgres_connection import connect_postgres
        return connect_postgres(dsn, dict_row, statement_timeout_ms=5000)
    except Exception as exc:
        raise IdentityUnavailable("tenant identity storage is unavailable") from exc


def authenticate_api_key(
    token: str,
    tenant_id: str | None,
    *,
    dsn: str | None = None,
    pepper: str | None = None,
    connect_factory: Callable[[], Any] | None = None,
) -> Principal:
    """Authenticate one credential against one explicit active tenant membership."""
    selected_tenant = normalize_tenant_id(tenant_id)
    secret = pepper if pepper is not None else os.environ.get("OMNIS_API_KEY_PEPPER", "")
    token_digest = digest_api_key(token, secret)
    database_url = dsn if dsn is not None else os.environ.get("OMNIS_DATABASE_URL", "")
    if not database_url:
        raise IdentityUnavailable("PostgreSQL tenant identity is not configured")
    try:
        with _connect(database_url, connect_factory) as db:
            with db.cursor() as cur:
                cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (selected_tenant,))
                cur.execute(
                    """SELECT t.tenant_id, p.principal_id, p.email, p.display_name,
                              m.role, c.token_prefix
                       FROM omnis.api_credential AS c
                       JOIN omnis.principal AS p ON p.principal_id = c.principal_id
                       JOIN omnis.tenant_membership AS m
                         ON m.principal_id = p.principal_id AND m.tenant_id = c.tenant_id
                       JOIN omnis.tenant AS t ON t.tenant_id = c.tenant_id
                       WHERE c.token_digest = %s
                         AND c.tenant_id = %s
                         AND t.tenant_id = %s
                         AND c.token_prefix = %s
                         AND c.revoked_at IS NULL
                         AND (c.expires_at IS NULL OR c.expires_at > now())
                         AND p.status = 'active'
                         AND m.status = 'active'
                         AND t.status = 'active'
                       LIMIT 1""",
                    (token_digest, selected_tenant, selected_tenant, token[:32]),
                )
                row = cur.fetchone()
    except IdentityUnavailable:
        raise
    except Exception as exc:
        raise IdentityUnavailable("tenant identity lookup failed") from exc
    if not row:
        raise InvalidCredential("invalid credential or inactive tenant membership")
    return Principal(
        tenant_id=str(row["tenant_id"]),
        principal_id=str(row["principal_id"]),
        email=row["email"],
        display_name=row["display_name"],
        role=row["role"],
        credential_prefix=row["token_prefix"],
    )
