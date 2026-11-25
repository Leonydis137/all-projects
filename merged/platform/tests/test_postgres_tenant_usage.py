"""Live PostgreSQL tests for tenant usage accounting and transaction guarantees."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

DSN = os.environ.get("OMNIS_TEST_DATABASE_URL", "").strip()
MIGRATIONS = (
    "001_evidence_and_audit.sql",
    "002_ledger_immutability.sql",
    "003_audit_event_canonical_payload.sql",
    "004_evidence_idempotency.sql",
    "005_case_insensitive_source_uri.sql",
    "006_tenant_identity.sql",
    "007_tenant_evidence.sql",
    "008_identity_row_security.sql",
    "009_tenant_bound_credentials.sql",
    "010_tenant_audit.sql",
    "011_tenant_decision_rules.sql",
    "012_tenant_assistant_conversations.sql",
    "013_tenant_usage_metering.sql",
    "014_tenant_usage_policy_member_reads.sql",
    "015_tenant_audit_active_actor.sql",
    "016_tenant_evidence_and_rules_active_actor.sql",
    "017_tenant_lifecycle_storage_rls.sql",
)


@pytest.fixture(scope="session")
def postgres_dsn():
    if not DSN:
        pytest.skip("OMNIS_TEST_DATABASE_URL is not configured")
    psycopg = pytest.importorskip("psycopg")
    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    with psycopg.connect(DSN, autocommit=True) as db:
        for name in MIGRATIONS:
            db.execute((migration_dir / name).read_text(encoding="utf-8"))
    return DSN


def _tenant(dsn: str, monthly_limit: int | None):
    import psycopg

    marker = uuid4().hex
    tenant_id, principal_id = uuid4(), uuid4()
    with psycopg.connect(dsn) as db:
        db.execute("SELECT set_config('omnis.tenant_id', %s, true)", (str(tenant_id),))
        db.execute(
            "INSERT INTO omnis.tenant (tenant_id, slug, display_name) VALUES (%s, %s, %s)",
            (tenant_id, "usage-" + marker[:24], "Usage integration " + marker[:12]),
        )
        db.execute(
            "INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
            (principal_id, f"usage-{marker}@example.test", "Usage integration owner"),
        )
        db.execute(
            "INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) "
            "VALUES (%s, %s, 'owner', 'active')",
            (tenant_id, principal_id),
        )
        if monthly_limit is not None:
            db.execute(
                "INSERT INTO omnis.tenant_usage_policy "
                "(tenant_id, monthly_request_limit, updated_by) VALUES (%s, %s, %s)",
                (tenant_id, monthly_limit, principal_id),
            )
    return str(tenant_id), str(principal_id)


def _stores(dsn: str):
    from omnis.postgres_tenant_audit import PostgresTenantAuditLog
    from omnis.tenant_usage import TenantUsageStore

    return TenantUsageStore(dsn), PostgresTenantAuditLog(dsn)


def test_concurrent_usage_consumption_never_exceeds_minute_limit(postgres_dsn):
    from omnis.tenant_usage import TenantUsageError

    tenant_id, principal_id = _tenant(postgres_dsn, monthly_limit=None)
    usage, audit = _stores(postgres_dsn)

    def consume(_):
        try:
            usage.consume(tenant_id, principal_id, "integration.concurrent", 4, audit)
            return "accepted"
        except TenantUsageError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(consume, range(20)))

    assert outcomes.count("accepted") == 4
    assert outcomes.count("rate_limited") == 16

    summary = usage.summary(tenant_id, principal_id, audit)
    assert summary["accepted_requests"] == 4
    assert sum(row["events"] for row in summary["usage"]) == 20
    assert audit.verify(tenant_id)["valid"] is True


def test_monthly_quota_is_enforced_against_committed_accepted_events(postgres_dsn):
    from omnis.tenant_usage import TenantUsageError

    tenant_id, principal_id = _tenant(postgres_dsn, monthly_limit=3)
    usage, audit = _stores(postgres_dsn)

    outcomes = []
    for _ in range(5):
        try:
            usage.consume(tenant_id, principal_id, "integration.monthly", 100, audit)
            outcomes.append("accepted")
        except TenantUsageError as exc:
            outcomes.append(str(exc))

    assert outcomes == ["accepted", "accepted", "accepted", "quota_exceeded", "quota_exceeded"]
    summary = usage.summary(tenant_id, principal_id, audit)
    assert summary["accepted_requests"] == 3
    assert summary["monthly_request_limit"] == 3
    assert audit.verify(tenant_id)["valid"] is True


def test_audit_failure_rolls_back_usage_event_and_minute_counter(postgres_dsn):
    import psycopg

    from omnis.tenant_usage import TenantUsageStore, TenantUsageUnavailable

    tenant_id, principal_id = _tenant(postgres_dsn, monthly_limit=None)
    usage = TenantUsageStore(postgres_dsn)

    class FailingAudit:
        def record_in_transaction(self, db, kind, payload, actor=None):
            raise RuntimeError("forced audit persistence failure")

    with pytest.raises(TenantUsageUnavailable, match="storage is unavailable"):
        usage.consume(tenant_id, principal_id, "integration.rollback", 10, FailingAudit())

    with psycopg.connect(postgres_dsn) as db:
        event_count = db.execute(
            "SELECT count(*) FROM omnis.tenant_usage_event WHERE tenant_id = %s",
            (tenant_id,),
        ).fetchone()[0]
        minute_count = db.execute(
            "SELECT coalesce(sum(request_count), 0) FROM omnis.tenant_usage_minute WHERE tenant_id = %s",
            (tenant_id,),
        ).fetchone()[0]

    assert event_count == 0
    assert minute_count == 0

    # The failed transaction consumed no quota or rate-limit capacity.
    _, audit = _stores(postgres_dsn)
    result = usage.consume(tenant_id, principal_id, "integration.after_rollback", 1, audit)
    assert result["outcome"] == "accepted"
    assert result["minute_requests"] == 1
    assert audit.verify(tenant_id)["valid"] is True
