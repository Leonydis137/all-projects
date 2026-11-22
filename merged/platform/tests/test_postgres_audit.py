"""Live PostgreSQL audit-log integration tests."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

DSN = os.environ.get("OMNIS_TEST_DATABASE_URL", "").strip()


@pytest.fixture(scope="session")
def postgres_audit_dsn():
    if not DSN:
        pytest.skip("OMNIS_TEST_DATABASE_URL is not configured")
    psycopg = pytest.importorskip("psycopg")
    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    with psycopg.connect(DSN, autocommit=True) as db:
        for name in (
            "001_evidence_and_audit.sql",
            "002_ledger_immutability.sql",
            "003_audit_event_canonical_payload.sql",
        ):
            db.execute((migration_dir / name).read_text(encoding="utf-8"))
    return DSN


def test_postgres_audit_append_list_verify(postgres_audit_dsn):
    from omnis.postgres_audit import PostgresAuditLog

    marker = uuid4().hex
    log = PostgresAuditLog(postgres_audit_dsn, actor="integration-test")
    first = log.record("test.created", {"marker": marker, "count": 1})
    second = log.record("test.updated", {"marker": marker, "count": 2})
    assert second["prev"] == first["hash"]
    assert second["actor"] == "integration-test"
    listed = log.list(limit=10)
    assert any(item["hash"] == first["hash"] for item in listed)
    assert any(item["hash"] == second["hash"] for item in listed)
    assert log.verify() is True


def test_postgres_audit_concurrent_appends_are_serialized(postgres_audit_dsn):
    from omnis.postgres_audit import PostgresAuditLog

    marker = uuid4().hex

    def append(index: int):
        return PostgresAuditLog(postgres_audit_dsn).record("test.concurrent", {"marker": marker, "index": index})

    with ThreadPoolExecutor(max_workers=4) as pool:
        events = list(pool.map(append, range(4)))
    assert len({event["hash"] for event in events}) == 4
    assert PostgresAuditLog(postgres_audit_dsn).verify() is True


def test_postgres_audit_rejects_mutation(postgres_audit_dsn):
    import psycopg
    from omnis.postgres_audit import PostgresAuditLog

    event = PostgresAuditLog(postgres_audit_dsn).record("test.immutable", {"marker": uuid4().hex})
    with pytest.raises(psycopg.Error):
        with psycopg.connect(postgres_audit_dsn) as db:
            db.execute("UPDATE omnis.audit_event SET actor = 'tampered' WHERE event_hash = %s", (event["hash"],))
    assert PostgresAuditLog(postgres_audit_dsn).verify() is True


def test_json_payload_comparison_is_type_sensitive():
    from omnis.postgres_audit import _json_equal

    assert _json_equal({"value": 1}, {"value": 1})
    assert not _json_equal({"value": 1}, {"value": True})
    assert not _json_equal({"value": 0}, {"value": False})


def test_postgres_audit_decode_handles_non_utc_session_timezone(postgres_audit_dsn):
    import psycopg
    from psycopg.rows import dict_row
    from omnis.postgres_audit import PostgresAuditLog

    log = PostgresAuditLog(postgres_audit_dsn)
    log.record("test.timezone", {"marker": uuid4().hex})
    with psycopg.connect(postgres_audit_dsn, row_factory=dict_row) as db:
        db.execute("SET TIME ZONE 'America/Los_Angeles'")
        row = db.execute(
            """SELECT occurred_at, actor, event_type, payload, previous_hash, event_hash, event_json
               FROM omnis.audit_event ORDER BY sequence DESC LIMIT 1"""
        ).fetchone()
    event = log._decode(row)
    assert event["kind"] == "test.timezone"
