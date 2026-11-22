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
    return DSN


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

    ledger = PostgresEvidenceLedger(postgres_dsn)
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
        return PostgresEvidenceLedger(postgres_dsn).append(_record(f"{marker}-{index}"))

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(append, range(4)))
    assert len({row["sequence"] for row in rows}) == 4
    assert PostgresEvidenceLedger(postgres_dsn).verify()["valid"] is True


def test_postgres_ledger_rejects_update_delete_and_truncate(postgres_dsn):
    import psycopg
    from omnis.postgres_evidence import PostgresEvidenceLedger

    ledger = PostgresEvidenceLedger(postgres_dsn)
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
        before = db.execute("SELECT count(*) AS n FROM omnis.evidence").fetchone()[0]

    class FailingAudit:
        def record_in_transaction(self, db, kind, payload):
            raise RuntimeError("simulated audit failure")

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        ledger.append_with_audit(_record(marker), FailingAudit())
    with psycopg.connect(postgres_dsn) as db:
        after_failure = db.execute("SELECT count(*) AS n FROM omnis.evidence").fetchone()["n"]
    assert after_failure == before

    appended = ledger.append_with_audit(_record(marker), audit)
    assert appended["submitted_by"] == marker
    assert audit.verify() is True


def test_postgres_evidence_idempotency(postgres_dsn):
    from omnis.evidence import EvidenceValidationError
    from omnis.postgres_evidence import PostgresEvidenceLedger

    ledger = PostgresEvidenceLedger(postgres_dsn)
    key = "retry-" + uuid4().hex
    first = ledger.append({**_record("idempotent"), "idempotency_key": key})
    retry = ledger.append({**_record("idempotent"), "idempotency_key": key})
    assert retry["sequence"] == first["sequence"]
    assert retry["record_hash"] == first["record_hash"]
    with pytest.raises(EvidenceValidationError, match="different evidence record"):
        ledger.append({**_record("different"), "idempotency_key": key})
