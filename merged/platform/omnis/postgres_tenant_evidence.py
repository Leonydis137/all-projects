"""Tenant-scoped PostgreSQL evidence ledger with RLS and per-tenant hash chains."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from .evidence import EvidenceValidationError, _canonical, _validate
from .postgres_evidence import EvidenceIntegrityError, PostgresEvidenceLedger

_LOG = logging.getLogger(__name__)


class PostgresTenantEvidenceLedger:
    """Append-only evidence store whose reads and writes are bound to one tenant."""

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
    def _tenant(value: str) -> str:
        try:
            return str(UUID(str(value)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise EvidenceValidationError("tenant_id must be a UUID") from exc

    @staticmethod
    def _scope(cur, tenant_id: str, actor_id: str | None = None) -> None:
        cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_id,))
        if actor_id is not None:
            cur.execute("SELECT set_config('omnis.principal_id', %s, true)", (actor_id,))

    @staticmethod
    def _decode(row: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        try:
            if str(row["tenant_id"]) != tenant_id:
                raise EvidenceIntegrityError("tenant evidence row escaped its tenant scope")
            record = PostgresEvidenceLedger._record(row)
            raw_record = {key: value for key, value in record.items()
                          if key not in {"sequence", "previous_hash", "record_hash", "source_authenticity"}}
            clean = _validate(raw_record)
            if _canonical(raw_record) != _canonical(clean):
                raise EvidenceIntegrityError("stored tenant evidence record is not canonical")
            return {"tenant_id": tenant_id, **record, **clean}
        except (EvidenceValidationError, EvidenceIntegrityError):
            raise
        except Exception as exc:
            raise EvidenceIntegrityError("stored tenant evidence record is malformed") from exc

    def _head_hash(self, cur, tenant_id: str) -> str:
        cur.execute(
            """SELECT tenant_id, sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                      declared_license, submitted_by, idempotency_key, record_json,
                      previous_hash, record_hash
               FROM omnis.tenant_evidence
               WHERE tenant_id = %s ORDER BY sequence DESC LIMIT 2""",
            (tenant_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return "0" * 64
        latest_record = self._decode(rows[0], tenant_id)
        latest_clean = {key: latest_record[key] for key in (
            "source_uri", "content_sha256", "acquired_at", "acquisition_method",
            "license", "submitted_by", "idempotency_key", "provenance_attestation"
        ) if key in latest_record}
        latest_expected = hashlib.sha256(_canonical({
            "tenant_id": tenant_id, "record": latest_clean,
            "previous_hash": rows[0]["previous_hash"],
        })).hexdigest()
        if latest_expected != rows[0]["record_hash"]:
            raise EvidenceIntegrityError("tenant evidence head failed integrity verification")
        if len(rows) > 1:
            previous_record = self._decode(rows[1], tenant_id)
            previous_clean = {key: previous_record[key] for key in (
                "source_uri", "content_sha256", "acquired_at", "acquisition_method",
                "license", "submitted_by", "idempotency_key", "provenance_attestation"
            ) if key in previous_record}
            previous_expected = hashlib.sha256(_canonical({
                "tenant_id": tenant_id, "record": previous_clean,
                "previous_hash": rows[1]["previous_hash"],
            })).hexdigest()
            if (previous_expected != rows[1]["record_hash"]
                    or rows[0]["previous_hash"] != rows[1]["record_hash"]):
                raise EvidenceIntegrityError("tenant evidence predecessor failed integrity verification")
        elif rows[0]["previous_hash"] != "0" * 64:
            raise EvidenceIntegrityError("tenant evidence first record has an invalid predecessor")
        return rows[0]["record_hash"]

    def append_with_audit(
        self, record: dict[str, Any], tenant_id: str, actor_id: str, audit_log,
    ) -> dict[str, Any]:
        tenant = self._tenant(tenant_id)
        actor = self._tenant(actor_id)
        supplied = dict(record)
        supplied["submitted_by"] = actor
        clean = _validate(supplied)
        stamp = datetime.fromisoformat(clean["acquired_at"].replace("Z", "+00:00"))
        payload_json = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self._connect() as db:
            with db.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                self._scope(cur, tenant, actor)
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                            (f"omnis.tenant_evidence:{tenant}",))
                previous_hash = self._head_hash(cur, tenant)
                if clean.get("idempotency_key"):
                    cur.execute(
                        """SELECT tenant_id, sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                                  declared_license, submitted_by, idempotency_key, record_json,
                                  previous_hash, record_hash
                           FROM omnis.tenant_evidence
                           WHERE tenant_id = %s AND idempotency_key = %s""",
                        (tenant, clean["idempotency_key"]),
                    )
                    existing = cur.fetchone()
                    if existing:
                        decoded_existing = self._decode(existing, tenant)
                        stored = existing["record_json"]
                        if isinstance(stored, str):
                            stored = json.loads(stored)
                        if _canonical(stored) != _canonical(clean):
                            raise EvidenceValidationError(
                                "idempotency_key was already used for different evidence in this tenant"
                            )
                        expected = hashlib.sha256(_canonical({
                            "tenant_id": tenant, "record": stored,
                            "previous_hash": existing["previous_hash"],
                        })).hexdigest()
                        if expected != existing["record_hash"]:
                            raise EvidenceIntegrityError("existing tenant evidence row failed integrity verification")
                        audit_payload = json.dumps({
                            "tenant_id": tenant, "sequence": existing["sequence"],
                            "record_hash": existing["record_hash"],
                        }, sort_keys=True, separators=(",", ":"))
                        cur.execute(
                            """SELECT 1 FROM omnis.tenant_audit_event
                               WHERE tenant_id = %s AND event_type = 'tenant.evidence.append'
                                 AND payload = %s::jsonb LIMIT 1""",
                            (tenant, audit_payload),
                        )
                        if cur.fetchone() is None:
                            raise EvidenceIntegrityError("existing tenant evidence row has no audit event")
                        return {"sequence": existing["sequence"], "tenant_id": tenant, **stored,
                                "previous_hash": existing["previous_hash"],
                                "record_hash": existing["record_hash"],
                                "source_authenticity": "unverified", "idempotent_replay": True}
                digest = hashlib.sha256(_canonical({
                    "tenant_id": tenant, "record": clean, "previous_hash": previous_hash,
                })).hexdigest()
                cur.execute(
                    """INSERT INTO omnis.tenant_evidence
                       (tenant_id, source_uri, content_sha256, acquired_at, acquisition_method,
                        declared_license, submitted_by, record_json, previous_hash, record_hash, idempotency_key)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                       RETURNING sequence""",
                    (tenant, clean["source_uri"], clean["content_sha256"], stamp,
                     clean["acquisition_method"], clean["license"], actor,
                     payload_json, previous_hash, digest, clean.get("idempotency_key")),
                )
                sequence = cur.fetchone()["sequence"]
                audit_log.record_in_transaction(
                    db, "tenant.evidence.append",
                    {"tenant_id": tenant, "sequence": sequence, "record_hash": digest},
                    actor=actor,
                )
        return {"sequence": sequence, "tenant_id": tenant, **clean,
                "previous_hash": previous_hash, "record_hash": digest,
                "source_authenticity": "unverified"}

    def list(self, tenant_id: str, limit: int = 100, before: int | None = None) -> list[dict[str, Any]]:
        tenant = self._tenant(tenant_id)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise EvidenceValidationError("limit must be an integer between 1 and 500")
        if before is not None and (isinstance(before, bool) or not isinstance(before, int) or before < 1):
            raise EvidenceValidationError("before must be a positive integer sequence cursor")
        with self._connect() as db:
            with db.cursor() as cur:
                self._scope(cur, tenant)
                if before is None:
                    cur.execute(
                        """SELECT tenant_id, sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                                  declared_license, submitted_by, idempotency_key, record_json,
                                  previous_hash, record_hash
                           FROM omnis.tenant_evidence
                           WHERE tenant_id = %s ORDER BY sequence DESC LIMIT %s""",
                        (tenant, limit),
                    )
                else:
                    cur.execute(
                        """SELECT tenant_id, sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                                  declared_license, submitted_by, idempotency_key, record_json,
                                  previous_hash, record_hash
                           FROM omnis.tenant_evidence
                           WHERE tenant_id = %s AND sequence < %s
                           ORDER BY sequence DESC LIMIT %s""",
                        (tenant, before, limit),
                    )
                rows = cur.fetchall()
        return [self._decode(row, tenant) for row in reversed(rows)]

    def verify(self, tenant_id: str) -> dict[str, Any]:
        tenant = self._tenant(tenant_id)
        previous_hash = "0" * 64
        checked = 0
        try:
            with self._connect(statement_timeout_ms=self.verify_timeout_ms) as db:
                with db.cursor() as cur:
                    self._scope(cur, tenant)
                    cur.execute(
                        """SELECT tenant_id, sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                                  declared_license, submitted_by, idempotency_key, record_json,
                                  previous_hash, record_hash
                           FROM omnis.tenant_evidence
                           WHERE tenant_id = %s ORDER BY sequence""",
                        (tenant,),
                    )
                    rows = cur.fetchall()
            for row in rows:
                try:
                    decoded = self._decode(row, tenant)
                    clean = {key: decoded[key] for key in (
                        "source_uri", "content_sha256", "acquired_at", "acquisition_method",
                        "license", "submitted_by", "idempotency_key", "provenance_attestation"
                    ) if key in decoded}
                    expected = hashlib.sha256(_canonical({
                        "tenant_id": tenant, "record": clean, "previous_hash": previous_hash,
                    })).hexdigest()
                    if row["previous_hash"] != previous_hash or row["record_hash"] != expected:
                        return {"valid": False, "checked": checked,
                                "failed_sequence": row["sequence"], "reason": "hash_mismatch"}
                except (EvidenceIntegrityError, EvidenceValidationError, TypeError, ValueError, KeyError):
                    return {"valid": False, "checked": checked,
                            "failed_sequence": row["sequence"], "reason": "malformed_record"}
                previous_hash = expected
                checked += 1
            return {"valid": True, "checked": checked, "head": previous_hash}
        except Exception as exc:
            _LOG.exception("OMNIS tenant evidence verification failed")
            reason = "verification_timeout" if type(exc).__name__ in {"QueryCanceled", "QueryCanceledError"} else "storage_error"
            return {"valid": False, "checked": checked, "reason": reason}
