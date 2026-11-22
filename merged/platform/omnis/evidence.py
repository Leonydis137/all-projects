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
    return {key: record[key].strip() for key in required}


class EvidenceLedger:
    """SQLite-backed append-only hash chain; safe across process restarts."""

    def __init__(self, path: str | Path = DEFAULT_DB) -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS evidence (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE
                );
                CREATE TRIGGER IF NOT EXISTS evidence_no_update
                BEFORE UPDATE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_no_delete
                BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        clean = _validate(record)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT record_hash FROM evidence ORDER BY sequence DESC LIMIT 1").fetchone()
            previous_hash = previous["record_hash"] if previous else "0" * 64
            payload = {"record": clean, "previous_hash": previous_hash}
            digest = hashlib.sha256(_canonical(payload)).hexdigest()
            cursor = db.execute(
                "INSERT INTO evidence(record_json, previous_hash, record_hash) VALUES (?, ?, ?)",
                (json.dumps(clean, sort_keys=True), previous_hash, digest),
            )
            sequence = cursor.lastrowid
        return {"sequence": sequence, **clean, "previous_hash": previous_hash,
                "record_hash": digest, "source_authenticity": "unverified"}

    def list(self, limit: int = 100, before: int | None = None) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise EvidenceValidationError("limit must be between 1 and 500")
        with self._connect() as db:
            if before is None:
                rows = db.execute("SELECT * FROM evidence ORDER BY sequence DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = db.execute("SELECT * FROM evidence WHERE sequence < ? ORDER BY sequence DESC LIMIT ?",
                                  (before, limit)).fetchall()
        return [{"sequence": row["sequence"], **json.loads(row["record_json"]),
                 "previous_hash": row["previous_hash"], "record_hash": row["record_hash"],
                 "source_authenticity": "unverified"} for row in reversed(rows)]

    def verify(self) -> dict[str, Any]:
        previous_hash = "0" * 64
        checked = 0
        with self._connect() as db:
            rows = db.execute("SELECT * FROM evidence ORDER BY sequence").fetchall()
        for row in rows:
            record = json.loads(row["record_json"])
            payload = {"record": record, "previous_hash": previous_hash}
            expected = hashlib.sha256(_canonical(payload)).hexdigest()
            if row["previous_hash"] != previous_hash or row["record_hash"] != expected:
                return {"valid": False, "checked": checked, "failed_sequence": row["sequence"]}
            previous_hash = expected
            checked += 1
        return {"valid": True, "checked": checked, "head": previous_hash}
