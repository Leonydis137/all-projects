"""PostgreSQL-backed evidence ledger for OMNIS.

The PostgreSQL schema is provisioned by explicit migrations. This adapter never
creates or alters schema at application startup.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Callable

from .evidence import EvidenceValidationError, _canonical, _validate


class PostgresEvidenceLedger:
    """Append-only PostgreSQL hash chain using transaction-scoped advisory locking."""

    def __init__(self, dsn: str, connect_factory: Callable[[], Any] | None = None) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("OMNIS_DATABASE_URL must be a non-empty PostgreSQL connection string")
        self.dsn = dsn
        self._connect_factory = connect_factory

    def _connect(self):
        if self._connect_factory is not None:
            return self._connect_factory()
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("PostgreSQL storage requires psycopg; install platform requirements") from exc
        from psycopg.conninfo import conninfo_to_dict
        params = conninfo_to_dict(self.dsn)
        host = (params.get("host") or "").strip()
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        # Loopback CI/dev databases may not offer TLS; every non-local host must
        # authenticate its certificate and hostname to prevent MITM credential theft.
        sslmode = "disable" if host in local_hosts or host.startswith("/") else "verify-full"
        return psycopg.connect(self.dsn, row_factory=dict_row, sslmode=sslmode,
                               connect_timeout=5, options="-c statement_timeout=10000")

    @staticmethod
    def _record(row: dict[str, Any]) -> dict[str, Any]:
        payload = row["record_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise EvidenceValidationError("stored evidence record is malformed")
        return {
            "sequence": row["sequence"],
            **payload,
            "previous_hash": row["previous_hash"],
            "record_hash": row["record_hash"],
            # Authenticity is not yet part of the hash commitment; ignore the mutable column.
            "source_authenticity": "unverified",
        }

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        clean = _validate(record)
        stamp = datetime.fromisoformat(clean["acquired_at"].replace("Z", "+00:00"))
        payload_json = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self._connect() as db:
            with db.cursor() as cur:
                # Serialize appends across processes so two writers cannot fork the chain.
                cur.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                cur.execute("SELECT pg_advisory_xact_lock(hashtext('omnis.evidence'))")
                if clean.get("idempotency_key"):
                    cur.execute(
                        """SELECT sequence, record_json, previous_hash, record_hash
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
        return {"sequence": sequence, **clean, "previous_hash": previous_hash,
                "record_hash": digest, "source_authenticity": "unverified"}


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
                        """SELECT sequence, record_json, previous_hash, record_hash
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
                        """SELECT sequence, record_json, previous_hash, record_hash, source_authenticity
                           FROM omnis.evidence ORDER BY sequence DESC LIMIT %s""", (limit,)
                    )
                else:
                    cur.execute(
                        """SELECT sequence, record_json, previous_hash, record_hash, source_authenticity
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
                    cur.execute("""SELECT sequence, record_json, previous_hash, record_hash
                                   FROM omnis.evidence ORDER BY sequence DESC LIMIT 1""")
                    row = cur.fetchone()
            if row is None:
                return {"valid": True, "checked": 0, "head": "0" * 64}
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
            return {"valid": False, "checked": 0, "reason": "storage_error"}

    def health(self) -> dict[str, Any]:
        """Bounded latest-record probe; full-chain verification remains explicit."""
        try:
            with self._connect() as db:
                with db.cursor() as cur:
                    cur.execute("""SELECT sequence, record_json, previous_hash, record_hash
                                   FROM omnis.evidence ORDER BY sequence DESC LIMIT 1""")
                    row = cur.fetchone()
            if row is None:
                return {"valid": True, "checked": 0, "head": "0" * 64}
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
            return {"valid": False, "checked": 0, "reason": "storage_error"}

    def verify(self) -> dict[str, Any]:
        previous_hash = "0" * 64
        checked = 0
        try:
            with self._connect() as db:
                with db.cursor() as cur:
                    cur.execute(
                        """SELECT sequence, record_json, previous_hash, record_hash
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
                    expected = hashlib.sha256(
                        _canonical({"record": record, "previous_hash": previous_hash})
                    ).hexdigest()
                    if row["previous_hash"] != previous_hash or row["record_hash"] != expected:
                        return {"valid": False, "checked": checked,
                                "failed_sequence": row["sequence"], "reason": "hash_mismatch"}
                except (TypeError, ValueError, KeyError):
                    return {"valid": False, "checked": checked,
                            "failed_sequence": row["sequence"], "reason": "malformed_record"}
                previous_hash = expected
                checked += 1
            return {"valid": True, "checked": checked, "head": previous_hash}
        except Exception:
            return {"valid": False, "checked": checked, "reason": "storage_error"}
