"""Contract tests for the persistent evidence ledger; no fabricated evidence is inserted."""
import pytest

from omnis.evidence import EvidenceLedger, EvidenceValidationError


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
    record = {
        "source_uri": "file:///etc/passwd",
        "content_sha256": "a" * 64,
        "acquired_at": "2026-11-22T10:00:00",
        "acquisition_method": "direct-fetch",
        "license": "unknown",
        "submitted_by": "operator",
    }
    with pytest.raises(EvidenceValidationError):
        ledger.append(record)
    assert ledger.verify()["checked"] == 0
