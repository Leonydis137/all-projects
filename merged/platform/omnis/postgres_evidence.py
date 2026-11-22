"""PostgreSQL-backed evidence ledger for OMNIS.

The PostgreSQL schema is provisioned by explicit migrations. This adapter never
creates or alters schema at application startup.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable

from .evidence import EvidenceValidationError, _canonical, _validate


class EvidenceColumnMismatch(ValueError):
    """Denormalized SQL columns disagree with the canonical evidence JSON."""

_LOG = logging.getLogger(__name__)


class PostgresEvidenceLedger:
    """Append-only PostgreSQL hash chain using transaction-scoped advisory locking."""

    def __init__(self, dsn: str, connect_factory: Callable[[], Any] | None = None, *, audit_log=None) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("OMNIS_DATABASE_URL must be a non-empty PostgreSQL connection string")
        self.dsn = dsn
        self._connect_factory = connect_factory
        self._audit_log = audit_log
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
    def _record(row: dict[str, Any]) -> dict[str, Any]:
        payload = row["record_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise EvidenceValidationError("stored evidence record is malformed")
        expected_fields = {
            "source_uri": payload.get("source_uri"),
            "content_sha256": payload.get("content_sha256"),
            "acquisition_method": payload.get("acquisition_method"),
            "declared_license": payload.get("license"),
            "submitted_by": payload.get("submitted_by"),
            "idempotency_key": payload.get("idempotency_key"),
        }
        for column, expected_value in expected_fields.items():
            actual = row[column]
            if column == "content_sha256":
                actual = actual.strip()
            if actual != expected_value:
                raise EvidenceColumnMismatch(f"evidence column {column} differs from record_json")
        stored_time = row["acquired_at"]
        if stored_time.tzinfo is None:
            stored_time = stored_time.replace(tzinfo=timezone.utc)
        else:
            stored_time = stored_time.astimezone(timezone.utc)
        expected_time = datetime.fromisoformat(payload["acquired_at"].replace("Z", "+00:00")).astimezone(timezone.utc)
        if stored_time != expected_time:
            raise EvidenceColumnMismatch("evidence column acquired_at differs from record_json")
        return {
            "sequence": row["sequence"],
            **payload,
            "previous_hash": row["previous_hash"],
            "record_hash": row["record_hash"],
            # Authenticity is not yet part of the hash commitment; ignore the mutable column.
            "source_authenticity": "unverified",
        }

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        """Append through the configured audit log; unpaired writes are rejected."""
        if self._audit_log is None:
            raise RuntimeError("PostgreSQL evidence writes require an audit log; use append_with_audit")
        return self.append_with_audit(record, self._audit_log)

    def append_with_audit(self, record: dict[str, Any], audit_log) -> dict[str, Any]:
        """Commit evidence and its audit event atomically in one PostgreSQL transaction."""
        clean = _validate(record)
        stamp = datetime.fromisoformat(clean["acquired_at"].replace("Z", "+00:00"))
        payload_json = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self._connect() as db:
            with db.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                cur.execute("SELECT pg_advisory_xact_lock(hashtext('omnis.evidence'))")
                if clean.get("idempotency_key"):
                    cur.execute(
                        """SELECT sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                                  declared_license, submitted_by, idempotency_key, record_json, previous_hash, record_hash
                           FROM omnis.evidence WHERE idempotency_key = %s""",
                        (clean["idempotency_key"],),
                    )
                    existing = cur.fetchone()
                    if existing:
                        stored = existing["record_json"]
                        if isinstance(stored, str):
                            stored = json.loads(stored)
                        if _canonical(stored) != _canonical(clean):
                            raise EvidenceValidationError(
                                "idempotency_key was already used for a different evidence record"
                            )
                        audit_payload = json.dumps(
                            {"sequence": existing["sequence"], "record_hash": existing["record_hash"]},
                            sort_keys=True, separators=(",", ":"),
                        )
                        cur.execute(
                            """SELECT 1 FROM omnis.audit_event
                               WHERE event_type = 'evidence.append' AND payload = %s::jsonb LIMIT 1""",
                            (audit_payload,),
                        )
                        if cur.fetchone() is None:
                            raise RuntimeError("existing evidence row has no corresponding audit event")
                        return self._record(existing)
                cur.execute("SELECT record_hash FROM omnis.evidence ORDER BY sequence DESC LIMIT 1")
                previous = cur.fetchone()
                previous_hash = previous["record_hash"] if previous else "0" * 64
                digest = hashlib.sha256(_canonical({"record": clean, "previous_hash": previous_hash})).hexdigest()
                cur.execute(
                    """INSERT INTO omnis.evidence
                       (source_uri, content_sha256, acquired_at, acquisition_method,
                        declared_license, submitted_by, record_json, previous_hash, record_hash, idempotency_key)
                       VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                       RETURNING sequence""",
                    (clean["source_uri"], clean["content_sha256"], stamp,
                     clean["acquisition_method"], clean["license"], clean["submitted_by"],
                     payload_json, previous_hash, digest, clean.get("idempotency_key")),
                )
                sequence = cur.fetchone()["sequence"]
                audit_log.record_in_transaction(
                    db, "evidence.append", {"sequence": sequence, "record_hash": digest}
                )
        return {"sequence": sequence, **clean, "previous_hash": previous_hash,
                "record_hash": digest, "source_authenticity": "unverified"}

    def list(self, limit: int = 100, before: int | None = None) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise EvidenceValidationError("limit must be an integer between 1 and 500")
        if before is not None and (isinstance(before, bool) or not isinstance(before, int) or before < 1):
            raise EvidenceValidationError("before must be a positive integer sequence cursor")
        with self._connect() as db:
            with db.cursor() as cur:
                if before is None:
                    cur.execute(
                        """SELECT sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                                  declared_license, submitted_by, idempotency_key, record_json, previous_hash, record_hash, source_authenticity
                           FROM omnis.evidence ORDER BY sequence DESC LIMIT %s""", (limit,)
                    )
                else:
                    cur.execute(
                        """SELECT sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                                  declared_license, submitted_by, record_json, previous_hash, record_hash, source_authenticity
                           FROM omnis.evidence WHERE sequence < %s
                           ORDER BY sequence DESC LIMIT %s""", (before, limit)
                    )
                rows = cur.fetchall()
        return [self._record(row) for row in reversed(rows)]

    def health(self) -> dict[str, Any]:
        """Bounded latest-record probe; full-chain verification remains explicit."""
        try:
            with self._connect() as db:
                with db.cursor() as cur:
                    cur.execute("""SELECT sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                                          declared_license, submitted_by, record_json, previous_hash, record_hash
                                   FROM omnis.evidence ORDER BY sequence DESC LIMIT 1""")
                    row = cur.fetchone()
            if row is None:
                return {"valid": True, "checked": 0, "head": "0" * 64}
            self._record(row)
            record = row["record_json"]
            if isinstance(record, str):
                record = json.loads(record)
            if not isinstance(record, dict):
                raise ValueError("record is not an object")
            expected = hashlib.sha256(_canonical({"record": record, "previous_hash": row["previous_hash"]})).hexdigest()
            valid = expected == row["record_hash"]
            return {"valid": valid, "checked": 1, "head": row["record_hash"] if valid else None,
                    **({} if valid else {"failed_sequence": row["sequence"], "reason": "hash_mismatch"})}
        except Exception:
            _LOG.exception("OMNIS evidence health probe failed")
            return {"valid": False, "checked": 0, "reason": "storage_error"}

    def verify(self) -> dict[str, Any]:
        previous_hash = "0" * 64
        checked = 0
        try:
            with self._connect(statement_timeout_ms=self.verify_timeout_ms) as db:
                with db.cursor() as cur:
                    cur.execute(
                        """SELECT sequence, source_uri, content_sha256, acquired_at, acquisition_method,
                                  declared_license, submitted_by, record_json, previous_hash, record_hash
                           FROM omnis.evidence ORDER BY sequence"""
                    )
                    rows = cur.fetchall()
            for row in rows:
                try:
                    record = row["record_json"]
                    if isinstance(record, str):
                        record = json.loads(record)
                    if not isinstance(record, dict):
                        raise ValueError("record is not an object")
                    self._record(row)
                    expected = hashlib.sha256(
                        _canonical({"record": record, "previous_hash": previous_hash})
                    ).hexdigest()
                    if row["previous_hash"] != previous_hash or row["record_hash"] != expected:
                        return {"valid": False, "checked": checked,
                                "failed_sequence": row["sequence"], "reason": "hash_mismatch"}
                except EvidenceColumnMismatch:
                    return {"valid": False, "checked": checked,
                            "failed_sequence": row["sequence"], "reason": "column_mismatch"}
                except (TypeError, ValueError, KeyError):
                    return {"valid": False, "checked": checked,
                            "failed_sequence": row["sequence"], "reason": "malformed_record"}
                previous_hash = expected
                checked += 1
            return {"valid": True, "checked": checked, "head": previous_hash}
        except Exception as exc:
            _LOG.exception("OMNIS evidence-ledger verification failed")
            reason = "verification_timeout" if type(exc).__name__ in {"QueryCanceled", "QueryCanceledError"} else "storage_error"
            return {"valid": False, "checked": checked, "reason": reason,
                    "error_type": type(exc).__name__}
