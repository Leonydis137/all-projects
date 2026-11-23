"""Tenant-isolated PostgreSQL audit chains with forced RLS."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

_ZERO_HASH = "0" * 64
_LOG = logging.getLogger(__name__)


class TenantAuditIntegrityError(RuntimeError):
    """A tenant audit event or chain failed integrity validation."""


class TenantAuditValidationError(ValueError):
    """A tenant audit query or event is invalid."""


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")


class PostgresTenantAuditLog:
    """Per-tenant append-only hash chains; no cross-tenant list or verify operation."""

    def __init__(self, dsn: str, connect_factory: Callable[[], Any] | None = None) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("OMNIS_DATABASE_URL must be a non-empty PostgreSQL connection string")
        self.dsn = dsn
        self._connect_factory = connect_factory
        self.verify_timeout_ms = int(os.environ.get("OMNIS_DB_VERIFY_TIMEOUT_MS", "300000"))
        if self.verify_timeout_ms < 10_000:
            raise ValueError("OMNIS_DB_VERIFY_TIMEOUT_MS must be at least 10000")

    def _connect(self, statement_timeout_ms: int = 10_000):
        if self._connect_factory is not None:
            return self._connect_factory()
        from psycopg.rows import dict_row
        from .postgres_connection import connect_postgres
        return connect_postgres(self.dsn, dict_row, statement_timeout_ms=statement_timeout_ms)

    @staticmethod
    def _uuid(value: str, field: str) -> str:
        try:
            return str(UUID(str(value)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise TenantAuditValidationError(f"{field} must be a UUID") from exc

    @staticmethod
    def _scope(cur, tenant_id: str) -> None:
        cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_id,))

    @staticmethod
    def _decode(row: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        try:
            if str(row["tenant_id"]) != tenant_id:
                raise TenantAuditIntegrityError("tenant audit row escaped its tenant scope")
            raw = row["event_json"]
            event = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(event, dict):
                raise ValueError("event body is not an object")
            if (event.get("tenant_id") != tenant_id
                    or event.get("i") != row["event_index"]
                    or event.get("kind") != row["event_type"]
                    or event.get("actor") != row["actor"]
                    or event.get("prev") != row["previous_hash"]):
                raise ValueError("event columns differ from canonical body")
            if not isinstance(event.get("ts"), (int, float)) or isinstance(event.get("ts"), bool):
                raise ValueError("event timestamp is invalid")
            if not isinstance(event.get("payload"), dict):
                raise ValueError("event payload is invalid")
            stored = row["occurred_at"]
            if stored.tzinfo is None:
                stored = stored.replace(tzinfo=timezone.utc)
            else:
                stored = stored.astimezone(timezone.utc)
            if stored != datetime.fromtimestamp(event["ts"], tz=timezone.utc):
                raise ValueError("event timestamp column differs from canonical body")
            return event
        except TenantAuditIntegrityError:
            raise
        except Exception as exc:
            raise TenantAuditIntegrityError("stored tenant audit event is malformed") from exc

    def _append_cursor(self, cur, tenant: str, kind: str, payload: dict[str, Any], actor: str) -> dict[str, Any]:
        if not isinstance(kind, str) or not kind.strip() or len(kind) > 160:
            raise TenantAuditValidationError("event type must contain 1-160 characters")
        if not isinstance(payload, dict):
            raise TenantAuditValidationError("event payload must be an object")
        if len(_canonical(payload)) > 32_768:
            raise TenantAuditValidationError("event payload exceeds 32768 bytes")
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"omnis.tenant_audit:{tenant}",))
        cur.execute(
            """SELECT tenant_id, event_index, occurred_at, actor, event_type,
                      previous_hash, event_hash, event_json
               FROM omnis.tenant_audit_event
               WHERE tenant_id = %s ORDER BY event_index DESC LIMIT 2""",
            (tenant,),
        )
        rows = cur.fetchall()
        if rows:
            latest = self._decode(rows[0], tenant)
            latest_hash = hashlib.sha256(_canonical(latest)).hexdigest()
            if latest_hash != rows[0]["event_hash"]:
                raise TenantAuditIntegrityError("tenant audit chain head failed integrity verification")
            if len(rows) > 1:
                previous = self._decode(rows[1], tenant)
                previous_hash = hashlib.sha256(_canonical(previous)).hexdigest()
                if (previous_hash != rows[1]["event_hash"]
                        or latest["prev"] != rows[1]["event_hash"]
                        or latest["i"] != previous["i"] + 1):
                    raise TenantAuditIntegrityError("tenant audit predecessor failed integrity verification")
            elif latest["i"] != 0 or latest["prev"] != _ZERO_HASH:
                raise TenantAuditIntegrityError("tenant audit first event has an invalid predecessor")
            index, previous_hash = latest["i"] + 1, rows[0]["event_hash"]
        else:
            index, previous_hash = 0, _ZERO_HASH

        timestamp = time.time()
        body = {"tenant_id": tenant, "i": index, "ts": timestamp, "kind": kind.strip(),
                "payload": payload, "prev": previous_hash, "actor": actor}
        digest = hashlib.sha256(_canonical(body)).hexdigest()
        occurred_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        cur.execute(
            """INSERT INTO omnis.tenant_audit_event
               (tenant_id, event_index, occurred_at, actor, event_type, payload,
                previous_hash, event_hash, event_json)
               VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)""",
            (tenant, index, occurred_at, actor, kind.strip(),
             json.dumps(payload, sort_keys=True, default=str), previous_hash, digest,
             json.dumps(body, sort_keys=True, default=str, separators=(",", ":"))),
        )
        return {**body, "hash": digest}

    def record_in_transaction(self, db, kind: str, payload: dict[str, Any],
                              actor: str | None = None) -> dict[str, Any]:
        tenant = self._uuid(payload.get("tenant_id"), "tenant_id")
        principal = self._uuid(actor, "actor")
        with db.cursor() as cur:
            self._scope(cur, tenant)
            return self._append_cursor(cur, tenant, kind, payload, principal)

    def record(self, kind: str, payload: dict[str, Any],
               actor: str | None = None) -> dict[str, Any]:
        tenant = self._uuid(payload.get("tenant_id"), "tenant_id")
        principal = self._uuid(actor, "actor")
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant)
                result = self._append_cursor(cur, tenant, kind, payload, principal)
        return result

    def list(self, tenant_id: str, limit: int = 100, before: int | None = None) -> list[dict[str, Any]]:
        tenant = self._uuid(tenant_id, "tenant_id")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise TenantAuditValidationError("limit must be an integer between 1 and 500")
        if before is not None and (isinstance(before, bool) or not isinstance(before, int) or before < 0):
            raise TenantAuditValidationError("before must be a non-negative event index")
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant)
                if before is None:
                    cur.execute(
                        """SELECT tenant_id, event_index, occurred_at, actor, event_type,
                                  previous_hash, event_hash, event_json
                           FROM omnis.tenant_audit_event WHERE tenant_id = %s
                           ORDER BY event_index DESC LIMIT %s""", (tenant, limit))
                else:
                    cur.execute(
                        """SELECT tenant_id, event_index, occurred_at, actor, event_type,
                                  previous_hash, event_hash, event_json
                           FROM omnis.tenant_audit_event WHERE tenant_id = %s AND event_index < %s
                           ORDER BY event_index DESC LIMIT %s""", (tenant, before, limit))
                rows = cur.fetchall()
        events = []
        for row in reversed(rows):
            event = self._decode(row, tenant)
            if hashlib.sha256(_canonical(event)).hexdigest() != row["event_hash"]:
                raise TenantAuditIntegrityError("tenant audit event failed hash validation")
            events.append({**event, "hash": row["event_hash"]})
        return events

    def verify(self, tenant_id: str) -> dict[str, Any]:
        tenant = self._uuid(tenant_id, "tenant_id")
        checked, previous_hash = 0, _ZERO_HASH
        try:
            with self._connect(statement_timeout_ms=self.verify_timeout_ms) as db:
                with db.cursor() as cur:
                    cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    self._scope(cur, tenant)
                    cur.execute(
                        """SELECT tenant_id, event_index, occurred_at, actor, event_type,
                                  previous_hash, event_hash, event_json
                           FROM omnis.tenant_audit_event WHERE tenant_id = %s
                           ORDER BY event_index""", (tenant,))
                    rows = cur.fetchall()
            for row in rows:
                event = self._decode(row, tenant)
                expected = hashlib.sha256(_canonical(event)).hexdigest()
                if (event["i"] != checked or event["prev"] != previous_hash
                        or row["previous_hash"] != previous_hash or row["event_hash"] != expected):
                    return {"valid": False, "checked": checked,
                            "failed_index": row["event_index"], "reason": "chain_mismatch"}
                previous_hash, checked = expected, checked + 1
            return {"valid": True, "checked": checked, "head": previous_hash}
        except TenantAuditIntegrityError:
            return {"valid": False, "checked": checked, "reason": "malformed_event"}
        except Exception as exc:
            _LOG.exception("OMNIS tenant audit verification failed")
            reason = "verification_timeout" if type(exc).__name__ in {"QueryCanceled", "QueryCanceledError"} else "storage_error"
            return {"valid": False, "checked": checked, "reason": reason}

    def health(self, tenant_id: str) -> bool:
        result = self.verify(tenant_id)
        return bool(result.get("valid"))
