"""Live PostgreSQL evidence-ledger integration tests.

Set OMNIS_TEST_DATABASE_URL to a disposable PostgreSQL database. Migrations are
applied by this fixture; never point this variable at a production database.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

DSN = os.environ.get("OMNIS_TEST_DATABASE_URL", "").strip()


@pytest.fixture(scope="session")
def postgres_dsn():
    if not DSN:
        pytest.skip("OMNIS_TEST_DATABASE_URL is not configured")
    psycopg = pytest.importorskip("psycopg")
    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    with psycopg.connect(DSN, autocommit=True) as db:
        db.execute((migration_dir / "001_evidence_and_audit.sql").read_text(encoding="utf-8"))
        db.execute((migration_dir / "002_ledger_immutability.sql").read_text(encoding="utf-8"))
        db.execute((migration_dir / "003_audit_event_canonical_payload.sql").read_text(encoding="utf-8"))
        db.execute((migration_dir / "004_evidence_idempotency.sql").read_text(encoding="utf-8"))
        db.execute((migration_dir / "005_case_insensitive_source_uri.sql").read_text(encoding="utf-8"))
    return DSN


def _ledger(dsn: str):
    from omnis.postgres_audit import PostgresAuditLog
    from omnis.postgres_evidence import PostgresEvidenceLedger
    return PostgresEvidenceLedger(dsn, audit_log=PostgresAuditLog(dsn))


def _record(marker: str) -> dict:
    return {
        "source_uri": f"https://example.org/evidence/{marker}",
        "content_sha256": "a" * 64,
        "acquired_at": "2026-11-22T10:00:00Z",
        "acquisition_method": "integration-test-fetch",
        "license": "unknown",
        "submitted_by": marker,
    }


def test_postgres_append_list_and_verify(postgres_dsn):
    from omnis.postgres_evidence import PostgresEvidenceLedger

    ledger = _ledger(postgres_dsn)
    marker = "pg-" + uuid4().hex
    appended = ledger.append(_record(marker))
    listed = ledger.list(limit=10, before=appended["sequence"] + 1)
    match = next(item for item in listed if item["sequence"] == appended["sequence"])
    assert match["submitted_by"] == marker
    assert match["acquired_at"] == "2026-11-22T10:00:00Z"
    assert match["record_hash"] == appended["record_hash"]
    verified = ledger.verify()
    assert verified["valid"] is True
    assert verified["checked"] >= 1


def test_postgres_serializes_concurrent_appends(postgres_dsn):
    from omnis.postgres_evidence import PostgresEvidenceLedger

    marker = "concurrent-" + uuid4().hex

    def append(index: int):
        return _ledger(postgres_dsn).append(_record(f"{marker}-{index}"))

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(append, range(4)))
    assert len({row["sequence"] for row in rows}) == 4
    assert PostgresEvidenceLedger(postgres_dsn).verify()["valid"] is True


def test_postgres_ledger_rejects_update_delete_and_truncate(postgres_dsn):
    import psycopg
    from omnis.postgres_evidence import PostgresEvidenceLedger

    ledger = _ledger(postgres_dsn)
    row = ledger.append(_record("immutable-" + uuid4().hex))
    for statement in (
        "UPDATE omnis.evidence SET submitted_by = 'tampered' WHERE sequence = %s",
        "DELETE FROM omnis.evidence WHERE sequence = %s",
        "TRUNCATE omnis.evidence",
    ):
        with pytest.raises(psycopg.Error):
            with psycopg.connect(postgres_dsn) as db:
                if "%s" in statement:
                    db.execute(statement, (row["sequence"],))
                else:
                    db.execute(statement)


def test_evidence_and_audit_commit_atomically(postgres_dsn):
    import psycopg
    from omnis.postgres_audit import PostgresAuditLog
    from omnis.postgres_evidence import PostgresEvidenceLedger

    ledger = PostgresEvidenceLedger(postgres_dsn)
    audit = PostgresAuditLog(postgres_dsn, actor="atomic-test")
    marker = "atomic-" + uuid4().hex
    with psycopg.connect(postgres_dsn) as db:
        before_evidence = db.execute("SELECT count(*) FROM omnis.evidence").fetchone()[0]
        before_audit = db.execute("SELECT count(*) FROM omnis.audit_event").fetchone()[0]

    class FailingAudit:
        def record_in_transaction(self, db, kind, payload):
            raise RuntimeError("simulated audit failure")

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        ledger.append_with_audit(_record(marker), FailingAudit())
    with psycopg.connect(postgres_dsn) as db:
        after_failure_evidence = db.execute("SELECT count(*) FROM omnis.evidence").fetchone()[0]
        after_failure_audit = db.execute("SELECT count(*) FROM omnis.audit_event").fetchone()[0]
    assert after_failure_evidence == before_evidence
    assert after_failure_audit == before_audit

    appended = ledger.append_with_audit(_record(marker), audit)
    assert appended["submitted_by"] == marker
    with psycopg.connect(postgres_dsn) as db:
        paired_events = db.execute(
            """SELECT count(*) FROM omnis.audit_event
               WHERE event_type = 'evidence.append'
                 AND payload->>'sequence' = %s
                 AND payload->>'record_hash' = %s""",
            (str(appended["sequence"]), appended["record_hash"]),
        ).fetchone()[0]
    assert paired_events == 1
    assert audit.verify() is True


def test_postgres_evidence_idempotency(postgres_dsn):
    from omnis.evidence import EvidenceValidationError
    from omnis.postgres_evidence import PostgresEvidenceLedger

    ledger = _ledger(postgres_dsn)
    key = "retry-" + uuid4().hex
    first = ledger.append({**_record("idempotent"), "idempotency_key": key})
    retry = ledger.append({**_record("idempotent"), "idempotency_key": key})
    assert retry["sequence"] == first["sequence"]
    assert retry["record_hash"] == first["record_hash"]
    with pytest.raises(EvidenceValidationError, match="different evidence record"):
        ledger.append({**_record("different"), "idempotency_key": key})


def test_postgres_accepts_uppercase_http_scheme(postgres_dsn):
    from omnis.postgres_evidence import PostgresEvidenceLedger

    record = _record("uppercase-" + uuid4().hex)
    record["source_uri"] = record["source_uri"].replace("https://", "HTTPS://", 1)
    appended = _ledger(postgres_dsn).append(record)
    assert appended["source_uri"].startswith("HTTPS://")


def test_evidence_validation_rejects_nul_characters():
    from omnis.evidence import EvidenceValidationError, _validate

    record = _record("nul-" + uuid4().hex)
    record["submitted_by"] = "bad\x00value"
    with pytest.raises(EvidenceValidationError, match="NUL"):
        _validate(record)


def test_postgres_verification_detects_denormalized_column_mismatch(postgres_dsn):
    import hashlib
    import json
    import psycopg
    from datetime import datetime
    from omnis.evidence import _canonical, _validate

    clean = _validate(_record("column-mismatch-" + uuid4().hex))
    with psycopg.connect(postgres_dsn) as db:
        previous = db.execute(
            "SELECT record_hash FROM omnis.evidence ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous[0] if previous else "0" * 64
        digest = hashlib.sha256(_canonical({"record": clean, "previous_hash": previous_hash})).hexdigest()
        db.execute(
            """INSERT INTO omnis.evidence
               (source_uri, content_sha256, acquired_at, acquisition_method, declared_license,
                submitted_by, record_json, previous_hash, record_hash, idempotency_key)
               VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, NULL)""",
            ("https://mismatched.example/uri", clean["content_sha256"],
             datetime.fromisoformat(clean["acquired_at"].replace("Z", "+00:00")),
             clean["acquisition_method"], clean["license"],
             clean["submitted_by"], json.dumps(clean), previous_hash, digest),
        )
    result = _ledger(postgres_dsn).verify()
    assert result["valid"] is False
    assert result["reason"] == "column_mismatch"


def test_evidence_validation_rejects_oversized_idempotency_keys():
    from omnis.evidence import EvidenceValidationError, _validate

    record = {**_record("oversized-key"), "idempotency_key": "x" * 257}
    with pytest.raises(EvidenceValidationError, match="256 UTF-8 bytes"):
        _validate(record)

def test_postgres_preserves_signed_attestation_in_hash_chain(postgres_dsn):
    import base64
    import hashlib
    import json
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    marker = "attested-" + uuid4().hex
    record = _record(marker)
    statement = {
        "version": "omnis-fetch-attestation-v1",
        "claim": "platform_observed_fetch",
        "source_uri": record["source_uri"],
        "content_sha256": record["content_sha256"],
    }
    key = Ed25519PrivateKey.generate()
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    canonical = json.dumps(statement, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    record["provenance_attestation"] = {
        "statement": statement,
        "algorithm": "Ed25519",
        "key_id": hashlib.sha256(public_bytes).hexdigest(),
        "public_key_b64": base64.urlsafe_b64encode(public_bytes).decode("ascii").rstrip("="),
        "signature_b64": base64.urlsafe_b64encode(key.sign(canonical)).decode("ascii").rstrip("="),
    }

    ledger = _ledger(postgres_dsn)
    first = ledger.append(record)
    second = ledger.append(_record(marker + "-next"))
    listed = ledger.list(limit=10, before=second["sequence"] + 1)
    attested = next(item for item in listed if item["sequence"] == first["sequence"])
    assert attested["provenance_attestation"] == record["provenance_attestation"]
    assert ledger.verify()["valid"] is True
