"""Contract tests for the persistent evidence ledger; no fabricated evidence is inserted."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from omnis.evidence import EvidenceLedger, EvidenceValidationError


def _record(index: int = 1) -> dict:
    return {
        "source_uri": f"https://example.org/source/{index}",
        "content_sha256": f"{index:064x}",
        "acquired_at": "2026-11-22T10:00:00+00:00",
        "acquisition_method": "direct-fetch",
        "license": "unknown",
        "submitted_by": "test-operator",
    }


def test_in_memory_ledger_is_rejected_as_non_persistent():
    with pytest.raises(ValueError, match="file-backed"):
        EvidenceLedger(":memory:")


def test_empty_ledger_is_valid_and_persistent(tmp_path):
    path = tmp_path / "evidence.sqlite3"
    first = EvidenceLedger(path)
    assert first.verify() == {"valid": True, "checked": 0, "head": "0" * 64}
    assert EvidenceLedger(path).verify() == first.verify()


def test_evidence_requires_real_source_metadata(tmp_path):
    ledger = EvidenceLedger(tmp_path / "evidence.sqlite3")
    with pytest.raises(EvidenceValidationError):
        ledger.append({})
    assert ledger.verify()["checked"] == 0


def test_ledger_rejects_non_http_source_and_unzoned_timestamp(tmp_path):
    ledger = EvidenceLedger(tmp_path / "evidence.sqlite3")
    record = _record()
    record["source_uri"] = "file:///etc/passwd"
    record["acquired_at"] = "2026-11-22T10:00:00"
    with pytest.raises(EvidenceValidationError):
        ledger.append(record)
    assert ledger.verify()["checked"] == 0


def test_append_only_triggers_reject_update_and_delete(tmp_path):
    path = tmp_path / "evidence.sqlite3"
    ledger = EvidenceLedger(path)
    ledger.append(_record())
    with sqlite3.connect(path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE evidence SET record_json = '{}' WHERE sequence = 1")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM evidence WHERE sequence = 1")


def test_verification_detects_tampered_record(tmp_path):
    path = tmp_path / "evidence.sqlite3"
    ledger = EvidenceLedger(path)
    ledger.append(_record())
    with sqlite3.connect(path) as db:
        db.execute("DROP TRIGGER evidence_no_update")
        db.execute("UPDATE evidence SET record_json = ? WHERE sequence = 1", (json.dumps(_record(99)),))
    result = ledger.verify()
    assert result["valid"] is False
    assert result["failed_sequence"] == 1
    assert result["reason"] == "hash_mismatch"


def test_verification_reports_malformed_stored_json_without_raising(tmp_path):
    path = tmp_path / "evidence.sqlite3"
    ledger = EvidenceLedger(path)
    ledger.append(_record())
    with sqlite3.connect(path) as db:
        db.execute("DROP TRIGGER evidence_no_update")
        db.execute("UPDATE evidence SET record_json = '{broken' WHERE sequence = 1")
    result = ledger.verify()
    assert result["valid"] is False
    assert result["failed_sequence"] == 1
    assert result["reason"] == "malformed_record"


def test_pagination_returns_stable_sequence_order(tmp_path):
    ledger = EvidenceLedger(tmp_path / "evidence.sqlite3")
    for index in range(1, 6):
        ledger.append(_record(index))
    assert [r["sequence"] for r in ledger.list(limit=2)] == [4, 5]
    assert [r["sequence"] for r in ledger.list(limit=2, before=4)] == [2, 3]
    assert [r["sequence"] for r in ledger.list(limit=10, before=2)] == [1]


@pytest.mark.parametrize("limit", [0, -1, 501, "10", True])
def test_pagination_rejects_invalid_limit(tmp_path, limit):
    ledger = EvidenceLedger(tmp_path / "evidence.sqlite3")
    with pytest.raises(EvidenceValidationError):
        ledger.list(limit=limit)


@pytest.mark.parametrize("cursor", [0, -1, "2", True])
def test_pagination_rejects_invalid_cursor(tmp_path, cursor):
    ledger = EvidenceLedger(tmp_path / "evidence.sqlite3")
    with pytest.raises(EvidenceValidationError):
        ledger.list(before=cursor)


def test_api_auth_fails_closed_when_token_is_unset(monkeypatch):
    from fastapi import HTTPException
    from omnis import api

    monkeypatch.setattr(api.config, "API_TOKEN", "")
    with pytest.raises(HTTPException) as exc:
        api.auth(None)
    assert exc.value.status_code == 503


def test_api_auth_rejects_missing_or_wrong_bearer_token(monkeypatch):
    from fastapi import HTTPException
    from omnis import api

    monkeypatch.setattr(api.config, "API_TOKEN", "test-secret")
    with pytest.raises(HTTPException) as missing:
        api.auth(None)
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as wrong:
        api.auth("Bearer wrong")
    assert wrong.value.status_code == 401
    assert api.auth("Bearer test-secret") is None


def test_sqlite_idempotent_replay_is_marked(tmp_path):
    ledger = EvidenceLedger(tmp_path / "evidence.sqlite3")
    record = {**_record(), "idempotency_key": "request-123"}
    first = ledger.append(record)
    retry = ledger.append(record)
    assert first["sequence"] == retry["sequence"]
    assert retry["idempotent_replay"] is True


def test_concurrent_startup_serializes_legacy_sqlite_column_migration(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute(
            """CREATE TABLE evidence (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                record_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL UNIQUE
            )"""
        )

    def initialize(_):
        return EvidenceLedger(path)

    with ThreadPoolExecutor(max_workers=6) as pool:
        ledgers = list(pool.map(initialize, range(6)))
    assert len(ledgers) == 6
    with sqlite3.connect(path) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(evidence)")}
        indexes = {row[1] for row in db.execute("PRAGMA index_list(evidence)")}
    assert "idempotency_key" in columns
    assert "evidence_idempotency_key_uq" in indexes
