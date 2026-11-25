"""PostgreSQL RLS regression tests for tenant usage quota policies."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

DSN = os.environ.get("OMNIS_TEST_DATABASE_URL", "").strip()
TEST_ROLE = "omnis_usage_policy_rls_test"
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
def usage_policy_dsn():
    if not DSN:
        pytest.skip("OMNIS_TEST_DATABASE_URL is not configured")
    psycopg = pytest.importorskip("psycopg")
    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    with psycopg.connect(DSN, autocommit=True) as db:
        for name in MIGRATIONS:
            db.execute((migration_dir / name).read_text(encoding="utf-8"))
        db.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{TEST_ROLE}') THEN
                    CREATE ROLE {TEST_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS;
                END IF;
            END
            $$;
            """
        )
        db.execute(f"GRANT USAGE ON SCHEMA omnis TO {TEST_ROLE}")
        db.execute(
            f"GRANT SELECT ON omnis.tenant_usage_policy, omnis.tenant_membership, omnis.tenant, omnis.principal TO {TEST_ROLE}"
        )
    return DSN


def _insert_tenant_and_members(db, marker: str):
    tenant_id = uuid4()
    owner_id = uuid4()
    active_member_id = uuid4()
    suspended_member_id = uuid4()
    outsider_id = uuid4()

    db.execute(
        "INSERT INTO omnis.tenant (tenant_id, slug, display_name) VALUES (%s, %s, %s)",
        (tenant_id, "quota-" + marker[:24], "Quota policy test"),
    )
    for principal_id, suffix in (
        (owner_id, "owner"),
        (active_member_id, "member"),
        (suspended_member_id, "suspended"),
        (outsider_id, "outsider"),
    ):
        db.execute(
            "INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
            (principal_id, f"{suffix}-{marker}@example.test", suffix),
        )
    db.execute(
        """
        INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status)
        VALUES (%s, %s, 'owner', 'active'),
               (%s, %s, 'reader', 'active'),
               (%s, %s, 'reader', 'suspended')
        """,
        (tenant_id, owner_id, tenant_id, active_member_id, tenant_id, suspended_member_id),
    )
    db.execute(
        """
        INSERT INTO omnis.tenant_usage_policy (tenant_id, monthly_request_limit, updated_by)
        VALUES (%s, 37, %s)
        """,
        (tenant_id, owner_id),
    )
    return str(tenant_id), str(owner_id), str(active_member_id), str(suspended_member_id), str(outsider_id)


def _visible_quota(dsn: str, tenant_id: str, principal_id: str):
    import psycopg

    with psycopg.connect(dsn) as db:
        db.execute(f"SET LOCAL ROLE {TEST_ROLE}")
        db.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_id,))
        db.execute("SELECT set_config('omnis.principal_id', %s, true)", (principal_id,))
        return db.execute(
            "SELECT monthly_request_limit FROM omnis.tenant_usage_policy WHERE tenant_id = %s",
            (tenant_id,),
        ).fetchall()


def test_quota_policy_is_visible_to_active_members_not_only_updater(usage_policy_dsn):
    import psycopg

    marker = uuid4().hex
    with psycopg.connect(usage_policy_dsn) as db:
        tenant_id, owner_id, member_id, suspended_id, outsider_id = _insert_tenant_and_members(db, marker)

    # The owner wrote the policy, but another active member must still see it.
    assert _visible_quota(usage_policy_dsn, tenant_id, owner_id) == [(37,)]
    assert _visible_quota(usage_policy_dsn, tenant_id, member_id) == [(37,)]

    # Suspended members and principals with no membership must not see the row.
    assert _visible_quota(usage_policy_dsn, tenant_id, suspended_id) == []
    assert _visible_quota(usage_policy_dsn, tenant_id, outsider_id) == []


def test_quota_policy_rls_requires_matching_tenant_context(usage_policy_dsn):
    import psycopg

    marker = uuid4().hex
    with psycopg.connect(usage_policy_dsn) as db:
        tenant_id, owner_id, member_id, _, _ = _insert_tenant_and_members(db, marker)

    # A valid principal cannot read a tenant policy when the transaction context
    # names a different tenant, even if that principal is active in the first.
    other_tenant_id = str(uuid4())
    assert _visible_quota(usage_policy_dsn, other_tenant_id, member_id) == []
    assert _visible_quota(usage_policy_dsn, tenant_id, member_id) == [(37,)]


def test_quota_policy_table_keeps_forced_rls_and_read_only_runtime_access(usage_policy_dsn):
    import psycopg

    with psycopg.connect(usage_policy_dsn) as db:
        flags = db.execute(
            """
            SELECT relrowsecurity, relforcerowsecurity
            FROM pg_class WHERE oid = 'omnis.tenant_usage_policy'::regclass
            """
        ).fetchone()
        assert flags == (True, True)
        privileges = db.execute(
            """
            SELECT
                has_table_privilege(%s, 'omnis.tenant_usage_policy', 'SELECT'),
                has_table_privilege(%s, 'omnis.tenant_usage_policy', 'INSERT'),
                has_table_privilege(%s, 'omnis.tenant_usage_policy', 'UPDATE'),
                has_table_privilege(%s, 'omnis.tenant_usage_policy', 'DELETE')
            """,
            (TEST_ROLE, TEST_ROLE, TEST_ROLE, TEST_ROLE),
        ).fetchone()
        assert privileges == (True, False, False, False)


def test_quota_policy_is_hidden_for_disabled_principals_and_suspended_tenants(usage_policy_dsn):
    import psycopg

    marker = uuid4().hex
    with psycopg.connect(usage_policy_dsn) as db:
        tenant_id, owner_id, _, _, _ = _insert_tenant_and_members(db, marker)
        disabled_id = uuid4()
        db.execute("INSERT INTO omnis.principal (principal_id, email, display_name, status) VALUES (%s, %s, %s, 'disabled')",
                   (disabled_id, f"disabled-quota-{marker}@example.test", "Disabled"))
        db.execute("INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) VALUES (%s, %s, 'reader', 'active')",
                   (tenant_id, disabled_id))
        suspended_tenant, suspended_actor = uuid4(), uuid4()
        db.execute("INSERT INTO omnis.tenant (tenant_id, slug, display_name, status) VALUES (%s, %s, %s, 'suspended')",
                   (suspended_tenant, "quota-suspended-" + marker[:20], "Suspended quota tenant"))
        db.execute("INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
                   (suspended_actor, f"suspended-quota-{marker}@example.test", "Suspended tenant owner"))
        db.execute("INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) VALUES (%s, %s, 'owner', 'active')",
                   (suspended_tenant, suspended_actor))
        db.execute("INSERT INTO omnis.tenant_usage_policy (tenant_id, monthly_request_limit, updated_by) VALUES (%s, 9, %s)",
                   (suspended_tenant, suspended_actor))

    assert _visible_quota(usage_policy_dsn, tenant_id, str(disabled_id)) == []
    assert _visible_quota(usage_policy_dsn, str(suspended_tenant), str(suspended_actor)) == []
    assert _visible_quota(usage_policy_dsn, tenant_id, owner_id) == [(37,)]
