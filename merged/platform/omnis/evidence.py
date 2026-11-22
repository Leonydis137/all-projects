"""Persistent, append-only evidence ledger for OMNIS.

The ledger verifies record integrity, not the truth of a submitter's claims.
Source authenticity requires independent retrieval or cryptographic signatures.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

DEFAULT_DB = Path(os.environ.get("OMNIS_EVIDENCE_DB", "var/omnis-evidence.sqlite3"))
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EvidenceValidationError(ValueError):
    pass


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _validate(record: dict[str, Any]) -> dict[str, Any]:
    required = ("source_uri", "content_sha256", "acquired_at", "acquisition_method", "license", "submitted_by")
    missing = [key for key in required if not isinstance(record.get(key), str) or not record[key].strip()]
    if missing:
        raise EvidenceValidationError("required non-empty fields: " + ", ".join(missing))
    if any("\x00" in record[key] for key in required):
        raise EvidenceValidationError("evidence fields must not contain NUL characters")
    if not _SHA256.fullmatch(record["content_sha256"]):
        raise EvidenceValidationError("content_sha256 must be a lowercase SHA-256 hex digest")
    parsed = urlsplit(record["source_uri"])
    if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username or parsed.password:
        raise EvidenceValidationError("source_uri must be an absolute HTTP(S) URI without embedded credentials")
    try:
        stamp = datetime.fromisoformat(record["acquired_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceValidationError("acquired_at must be ISO-8601") from exc
    if stamp.tzinfo is None:
        raise EvidenceValidationError("acquired_at must include a timezone")
    clean = {key: record[key].strip() for key in required}
    idempotency_key = record.get("idempotency_key")
    if idempotency_key is not None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise EvidenceValidationError("idempotency_key must be a non-empty string when provided")
        if "\x00" in idempotency_key:
            raise EvidenceValidationError("idempotency_key must not contain NUL characters")
        try:
            key_length = len(idempotency_key.strip().encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise EvidenceValidationError("idempotency_key must be valid UTF-8 text") from exc
        if key_length > 256:
            raise EvidenceValidationError("idempotency_key must not exceed 256 UTF-8 bytes")
        clean["idempotency_key"] = idempotency_key.strip()
    return clean


class EvidenceLedger:
    """SQLite-backed append-only hash chain; safe across process restarts."""

    def __init__(self, path: str | Path = DEFAULT_DB) -> None:
        if str(path) == ":memory:":
            raise ValueError("OMNIS evidence ledger requires a persistent file-backed SQLite database")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS evidence (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE,
                    idempotency_key TEXT UNIQUE
                );
                CREATE TRIGGER IF NOT EXISTS evidence_no_update
                BEFORE UPDATE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_no_delete
                BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
            """)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(evidence)")}
            if "idempotency_key" not in columns:
                db.execute("ALTER TABLE evidence ADD COLUMN idempotency_key TEXT")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS evidence_idempotency_key_uq ON evidence(idempotency_key) WHERE idempotency_key IS NOT NULL")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        clean = _validate(record)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if clean.get("idempotency_key"):
                existing = db.execute("SELECT * FROM evidence WHERE idempotency_key = ?", (clean["idempotency_key"],)).fetchone()
                if existing:
                    stored = json.loads(existing["record_json"])
                    if _canonical(stored) != _canonical(clean):
                        raise EvidenceValidationError("idempotency_key was already used for a different evidence record")
                    return {"sequence": existing["sequence"], **stored,
                            "previous_hash": existing["previous_hash"], "record_hash": existing["record_hash"],
                            "source_authenticity": "unverified"}
            previous = db.execute("SELECT record_hash FROM evidence ORDER BY sequence DESC LIMIT 1").fetchone()
            previous_hash = previous["record_hash"] if previous else "0" * 64
            payload = {"record": clean, "previous_hash": previous_hash}
            digest = hashlib.sha256(_canonical(payload)).hexdigest()
            cursor = db.execute(
                "INSERT INTO evidence(record_json, previous_hash, record_hash, idempotency_key) VALUES (?, ?, ?, ?)",
                (json.dumps(clean, sort_keys=True), previous_hash, digest, clean.get("idempotency_key")),
            )
            sequence = cursor.lastrowid
        return {"sequence": sequence, **clean, "previous_hash": previous_hash,
                "record_hash": digest, "source_authenticity": "unverified"}

    def list(self, limit: int = 100, before: int | None = None) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise EvidenceValidationError("limit must be an integer between 1 and 500")
        if before is not None and (isinstance(before, bool) or not isinstance(before, int) or before < 1):
            raise EvidenceValidationError("before must be a positive integer sequence cursor")
        with self._connect() as db:
            if before is None:
                rows = db.execute("SELECT * FROM evidence ORDER BY sequence DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = db.execute("SELECT * FROM evidence WHERE sequence < ? ORDER BY sequence DESC LIMIT ?",
                                  (before, limit)).fetchall()
        result = []
        for row in reversed(rows):
            try:
                record = json.loads(row["record_json"])
                if not isinstance(record, dict):
                    raise ValueError("record is not an object")
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise EvidenceValidationError("stored evidence record is malformed") from exc
            result.append({"sequence": row["sequence"], **record,
                           "previous_hash": row["previous_hash"], "record_hash": row["record_hash"],
                           "source_authenticity": "unverified"})
        return result

    def health(self) -> dict[str, Any]:
        """Bounded latest-record probe; full-chain verification remains explicit."""
        try:
            with self._connect() as db:
                row = db.execute("SELECT * FROM evidence ORDER BY sequence DESC LIMIT 1").fetchone()
            if row is None:
                return {"valid": True, "checked": 0, "head": "0" * 64}
            record = json.loads(row["record_json"])
            if not isinstance(record, dict):
                raise ValueError("record is not an object")
            expected = hashlib.sha256(_canonical({"record": record, "previous_hash": row["previous_hash"]})).hexdigest()
            valid = expected == row["record_hash"]
            return {"valid": valid, "checked": 1, "head": row["record_hash"] if valid else None,
                    **({} if valid else {"failed_sequence": row["sequence"], "reason": "hash_mismatch"})}
        except (OSError, sqlite3.Error, TypeError, ValueError):
            return {"valid": False, "checked": 0, "reason": "storage_error"}

    def verify(self) -> dict[str, Any]:
        previous_hash = "0" * 64
        checked = 0
        try:
            with self._connect() as db:
                rows = db.execute("SELECT * FROM evidence ORDER BY sequence").fetchall()
            for row in rows:
                try:
                    record = json.loads(row["record_json"])
                    if not isinstance(record, dict):
                        raise ValueError("record is not an object")
                    payload = {"record": record, "previous_hash": previous_hash}
                    expected = hashlib.sha256(_canonical(payload)).hexdigest()
                    if row["previous_hash"] != previous_hash or row["record_hash"] != expected:
                        return {"valid": False, "checked": checked,
                                "failed_sequence": row["sequence"], "reason": "hash_mismatch"}
                except (TypeError, ValueError, KeyError, sqlite3.Error):
                    return {"valid": False, "checked": checked,
                            "failed_sequence": row["sequence"], "reason": "malformed_record"}
                previous_hash = expected
                checked += 1
            return {"valid": True, "checked": checked, "head": previous_hash}
        except (OSError, sqlite3.Error):
            # Do not expose database paths or low-level storage details in health output.
            return {"valid": False, "checked": checked, "reason": "storage_error"}
