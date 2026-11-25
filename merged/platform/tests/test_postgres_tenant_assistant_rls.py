"""Live PostgreSQL RLS tests for tenant assistant conversation isolation.

Set OMNIS_TEST_DATABASE_URL to a disposable PostgreSQL database. This suite
applies the platform migrations and uses a non-superuser, non-BYPASSRLS role.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

DSN = os.environ.get("OMNIS_TEST_DATABASE_URL", "").strip()
TEST_ROLE = "omnis_tenant_assistant_rls_test"
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
)


@pytest.fixture(scope="session")
def assistant_rls_dsn():
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
            f"GRANT SELECT, INSERT, UPDATE ON "
            f"omnis.tenant_assistant_conversation, omnis.tenant_assistant_message TO {TEST_ROLE}"
        )
        db.execute(
            f"GRANT SELECT ON omnis.tenant, omnis.principal, omnis.tenant_membership TO {TEST_ROLE}"
        )
        db.execute(f"GRANT SELECT, INSERT ON omnis.tenant_audit_event TO {TEST_ROLE}")
        db.execute(f"GRANT SELECT, INSERT ON omnis.tenant_evidence TO {TEST_ROLE}")
        db.execute(f"GRANT USAGE, SELECT ON SEQUENCE omnis.tenant_evidence_sequence_seq TO {TEST_ROLE}")
        db.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON omnis.tenant_decision_rule TO {TEST_ROLE}")
    return DSN


def _seed_two_tenants(dsn: str, marker: str):
    import psycopg

    tenant_a, tenant_b = uuid4(), uuid4()
    actor_a, actor_b = uuid4(), uuid4()
    conversation_a, conversation_b = uuid4(), uuid4()
    with psycopg.connect(dsn) as db:
        for tenant_id, slug in ((tenant_a, "assistant-a-"), (tenant_b, "assistant-b-")):
            db.execute(
                "INSERT INTO omnis.tenant (tenant_id, slug, display_name) VALUES (%s, %s, %s)",
                (tenant_id, slug + marker[:20], slug + "test"),
            )
        for principal_id, suffix in ((actor_a, "a"), (actor_b, "b")):
            db.execute(
                "INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
                (principal_id, f"assistant-{suffix}-{marker}@example.test", suffix),
            )
        db.execute(
            """
            INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status)
            VALUES (%s, %s, 'owner', 'active'), (%s, %s, 'owner', 'active')
            """,
            (tenant_a, actor_a, tenant_b, actor_b),
        )
        db.execute(
            """
            INSERT INTO omnis.tenant_assistant_conversation
                (tenant_id, conversation_id, created_by, title, message_count)
            VALUES (%s, %s, %s, 'Tenant A private thread', 2),
                   (%s, %s, %s, 'Tenant B private thread', 2)
            """,
            (tenant_a, conversation_a, actor_a, tenant_b, conversation_b, actor_b),
        )
        db.execute(
            """
            INSERT INTO omnis.tenant_assistant_message
                (tenant_id, conversation_id, message_index, role, content, actor_id)
            VALUES (%s, %s, 1, 'user', 'A private question', %s),
                   (%s, %s, 2, 'assistant', 'A private answer', NULL),
                   (%s, %s, 1, 'user', 'B private question', %s),
                   (%s, %s, 2, 'assistant', 'B private answer', NULL)
            """,
            (tenant_a, conversation_a, actor_a,
             tenant_a, conversation_a,
             tenant_b, conversation_b, actor_b,
             tenant_b, conversation_b),
        )
    return tuple(map(str, (tenant_a, actor_a, conversation_a, tenant_b, actor_b, conversation_b)))


def _runtime_connection(dsn: str):
    import psycopg

    db = psycopg.connect(dsn)
    db.execute(f"SET ROLE {TEST_ROLE}")
    return db


def test_assistant_storage_adapters_cannot_read_another_tenants_conversation(assistant_rls_dsn):
    from omnis.tenant_assistant import TenantAssistantStore, TenantConversationError

    marker = uuid4().hex
    tenant_a, actor_a, conversation_a, tenant_b, actor_b, conversation_b = (
        _seed_two_tenants(assistant_rls_dsn, marker)
    )
    store = TenantAssistantStore(
        assistant_rls_dsn,
        connect_factory=lambda: _runtime_connection(assistant_rls_dsn),
    )

    listed = store.list(tenant_a, actor_a)
    assert [item["conversation_id"] for item in listed] == [conversation_a]

    metadata, messages = store.history(tenant_a, actor_a, conversation_a)
    assert metadata["conversation_id"] == conversation_a
    assert messages == [
        {"role": "user", "content": "A private question"},
        {"role": "assistant", "content": "A private answer"},
    ]

    with pytest.raises(TenantConversationError, match="not found"):
        store.history(tenant_a, actor_a, conversation_b)

    # Even an explicit predicate naming tenant B cannot bypass tenant A's RLS context.
    with _runtime_connection(assistant_rls_dsn) as db:
        db.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_a,))
        db.execute("SELECT set_config('omnis.principal_id', %s, true)", (actor_a,))
        assert db.execute(
            "SELECT conversation_id FROM omnis.tenant_assistant_conversation "
            "WHERE tenant_id = %s AND conversation_id = %s",
            (tenant_b, conversation_b),
        ).fetchall() == []
        assert db.execute(
            "SELECT content FROM omnis.tenant_assistant_message "
            "WHERE tenant_id = %s AND conversation_id = %s",
            (tenant_b, conversation_b),
        ).fetchall() == []


def test_assistant_rls_requires_active_membership_and_matching_tenant_context(assistant_rls_dsn):
    import psycopg

    marker = uuid4().hex
    tenant_a, actor_a, conversation_a, _, _, _ = _seed_two_tenants(assistant_rls_dsn, marker)
    suspended_actor = str(uuid4())
    with psycopg.connect(assistant_rls_dsn) as db:
        db.execute(
            "INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
            (suspended_actor, f"suspended-{marker}@example.test", "Suspended member"),
        )
        db.execute(
            """
            INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status)
            VALUES (%s, %s, 'reader', 'suspended')
            """,
            (tenant_a, suspended_actor),
        )

    with _runtime_connection(assistant_rls_dsn) as db:
        db.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_a,))
        db.execute("SELECT set_config('omnis.principal_id', %s, true)", (suspended_actor,))
        assert db.execute(
            "SELECT conversation_id FROM omnis.tenant_assistant_conversation WHERE tenant_id = %s",
            (tenant_a,),
        ).fetchall() == []

    with _runtime_connection(assistant_rls_dsn) as db:
        db.execute("SELECT set_config('omnis.tenant_id', %s, true)", (str(uuid4()),))
        db.execute("SELECT set_config('omnis.principal_id', %s, true)", (actor_a,))
        assert db.execute(
            "SELECT conversation_id FROM omnis.tenant_assistant_conversation "
            "WHERE tenant_id = %s AND conversation_id = %s",
            (tenant_a, conversation_a),
        ).fetchall() == []


def test_assistant_tables_keep_forced_rls(assistant_rls_dsn):
    import psycopg

    with psycopg.connect(assistant_rls_dsn) as db:
        flags = db.execute(
            """
            SELECT relname, relrowsecurity, relforcerowsecurity
            FROM pg_class
            WHERE oid IN (
                'omnis.tenant_assistant_conversation'::regclass,
                'omnis.tenant_assistant_message'::regclass
            )
            ORDER BY relname
            """
        ).fetchall()
        assert flags == [
            ("tenant_assistant_conversation", True, True),
            ("tenant_assistant_message", True, True),
        ]

def test_tenant_audit_inserts_require_matching_active_actor_and_tenant(assistant_rls_dsn):
    import psycopg
    from omnis.postgres_tenant_audit import PostgresTenantAuditLog

    marker = uuid4().hex
    tenant_a, actor_a, _, tenant_b, actor_b, _ = _seed_two_tenants(assistant_rls_dsn, marker)
    suspended_actor, disabled_actor, spoofed_actor = uuid4(), uuid4(), uuid4()
    suspended_tenant, suspended_tenant_actor = uuid4(), uuid4()

    with psycopg.connect(assistant_rls_dsn) as db:
        db.execute(
            "INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
            (suspended_actor, f"audit-suspended-{marker}@example.test", "Suspended actor"),
        )
        db.execute(
            "INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) "
            "VALUES (%s, %s, 'reader', 'suspended')",
            (tenant_a, suspended_actor),
        )
        db.execute(
            "INSERT INTO omnis.principal (principal_id, email, display_name, status) "
            "VALUES (%s, %s, %s, 'disabled')",
            (disabled_actor, f"audit-disabled-{marker}@example.test", "Disabled actor"),
        )
        db.execute(
            "INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) "
            "VALUES (%s, %s, 'reader', 'active')",
            (tenant_a, disabled_actor),
        )
        db.execute(
            "INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
            (spoofed_actor, f"audit-spoofed-{marker}@example.test", "Alternate active actor"),
        )
        db.execute(
            "INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) "
            "VALUES (%s, %s, 'reader', 'active')",
            (tenant_a, spoofed_actor),
        )
        db.execute(
            "INSERT INTO omnis.tenant (tenant_id, slug, display_name, status) "
            "VALUES (%s, %s, %s, 'suspended')",
            (suspended_tenant, "audit-suspended-" + marker[:20], "Suspended audit tenant"),
        )
        db.execute(
            "INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
            (suspended_tenant_actor, f"audit-tenant-actor-{marker}@example.test", "Tenant actor"),
        )
        db.execute(
            "INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) "
            "VALUES (%s, %s, 'owner', 'active')",
            (suspended_tenant, suspended_tenant_actor),
        )

    audit = PostgresTenantAuditLog(
        assistant_rls_dsn,
        connect_factory=lambda: _runtime_connection(assistant_rls_dsn),
    )
    accepted = audit.record(
        "tenant.audit.accepted", {"tenant_id": tenant_a}, actor=actor_a
    )
    assert accepted["actor"] == actor_a

    # A caller cannot forge another active member as the event actor.
    with _runtime_connection(assistant_rls_dsn) as db:
        db.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_a,))
        db.execute("SELECT set_config('omnis.principal_id', %s, true)", (actor_a,))
        with pytest.raises(psycopg.Error):
            db.execute(
                """INSERT INTO omnis.tenant_audit_event
                   (tenant_id, event_index, occurred_at, actor, event_type, payload,
                    previous_hash, event_hash, event_json)
                   VALUES (%s, 999999, now(), %s, 'tenant.audit.spoofed', '{}'::jsonb,
                           %s, %s, '{}')""",
                (tenant_a, spoofed_actor, "0" * 64, "f" * 64),
            )

    # A principal from tenant B cannot write into tenant A's chain.
    with pytest.raises(psycopg.Error):
        audit.record("tenant.audit.cross_tenant", {"tenant_id": tenant_a}, actor=actor_b)

    # Membership suspension, principal disablement, and tenant suspension
    # each invalidate the database-level INSERT policy.
    with pytest.raises(psycopg.Error):
        audit.record("tenant.audit.suspended_member", {"tenant_id": tenant_a},
                     actor=str(suspended_actor))
    with pytest.raises(psycopg.Error):
        audit.record("tenant.audit.disabled_principal", {"tenant_id": tenant_a},
                     actor=str(disabled_actor))
    with pytest.raises(psycopg.Error):
        audit.record("tenant.audit.suspended_tenant", {"tenant_id": str(suspended_tenant)},
                     actor=str(suspended_tenant_actor))


def _attempt_tenant_evidence_insert(dsn, tenant_id, principal_id, submitted_by):
    with _runtime_connection(dsn) as db:
        db.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_id,))
        db.execute("SELECT set_config('omnis.principal_id', %s, true)", (principal_id,))
        db.execute(
            """INSERT INTO omnis.tenant_evidence
               (tenant_id, source_uri, content_sha256, acquired_at, acquisition_method,
                declared_license, submitted_by, record_json, previous_hash, record_hash)
               VALUES (%s, 'https://example.test/evidence', %s, now(), 'integration-test',
                       'unknown', %s, '{}'::jsonb, %s, %s)""",
            (tenant_id, "a" * 64, submitted_by, "0" * 64, "f" * 64),
        )


def _attempt_tenant_rule_insert(dsn, tenant_id, principal_id, updated_by):
    with _runtime_connection(dsn) as db:
        db.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_id,))
        db.execute("SELECT set_config('omnis.principal_id', %s, true)", (principal_id,))
        row = db.execute(
            """INSERT INTO omnis.tenant_decision_rule
               (tenant_id, name, field, comparison, value, action, priority, created_by, updated_by)
               VALUES (%s, %s, 'risk_score', '>=', '80'::jsonb, 'review', 10, %s, %s)
               RETURNING rule_id""",
            (tenant_id, "rule-" + uuid4().hex[:12], updated_by, updated_by),
        ).fetchone()
        return str(row[0])


def _attempt_tenant_rule_delete(dsn, tenant_id, principal_id, rule_id):
    with _runtime_connection(dsn) as db:
        db.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_id,))
        db.execute("SELECT set_config('omnis.principal_id', %s, true)", (principal_id,))
        db.execute(
            "DELETE FROM omnis.tenant_decision_rule WHERE tenant_id = %s AND rule_id = %s",
            (tenant_id, rule_id),
        )
        return db.execute("SELECT count(*) FROM omnis.tenant_decision_rule WHERE tenant_id = %s AND rule_id = %s",
                          (tenant_id, rule_id)).fetchone()[0]

def test_tenant_evidence_writes_require_matching_active_actor(assistant_rls_dsn):
    import psycopg

    marker = uuid4().hex
    tenant_a, actor_a, _, tenant_b, actor_b, _ = _seed_two_tenants(assistant_rls_dsn, marker)
    suspended_actor, disabled_actor, spoofed_actor = uuid4(), uuid4(), uuid4()
    with psycopg.connect(assistant_rls_dsn) as db:
        db.execute("INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
                   (suspended_actor, f"evidence-suspended-{marker}@example.test", "Suspended"))
        db.execute("INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) VALUES (%s, %s, 'reader', 'suspended')",
                   (tenant_a, suspended_actor))
        db.execute("INSERT INTO omnis.principal (principal_id, email, display_name, status) VALUES (%s, %s, %s, 'disabled')",
                   (disabled_actor, f"evidence-disabled-{marker}@example.test", "Disabled"))
        db.execute("INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) VALUES (%s, %s, 'reader', 'active')",
                   (tenant_a, disabled_actor))
        db.execute("INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
                   (spoofed_actor, f"evidence-spoof-{marker}@example.test", "Spoof target"))
        db.execute("INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) VALUES (%s, %s, 'reader', 'active')",
                   (tenant_a, spoofed_actor))

    _attempt_tenant_evidence_insert(assistant_rls_dsn, tenant_a, actor_a, actor_a)
    for principal, submitted in ((actor_a, spoofed_actor), (actor_b, actor_b),
                                 (suspended_actor, suspended_actor), (disabled_actor, disabled_actor)):
        with pytest.raises(psycopg.Error):
            _attempt_tenant_evidence_insert(assistant_rls_dsn, tenant_a, principal, submitted)


def test_tenant_decision_rule_writes_require_matching_active_actor(assistant_rls_dsn):
    import psycopg

    marker = uuid4().hex
    tenant_a, actor_a, _, tenant_b, actor_b, _ = _seed_two_tenants(assistant_rls_dsn, marker)
    suspended_actor, disabled_actor = uuid4(), uuid4()
    with psycopg.connect(assistant_rls_dsn) as db:
        db.execute("INSERT INTO omnis.principal (principal_id, email, display_name) VALUES (%s, %s, %s)",
                   (suspended_actor, f"rule-suspended-{marker}@example.test", "Suspended"))
        db.execute("INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) VALUES (%s, %s, 'reader', 'suspended')",
                   (tenant_a, suspended_actor))
        db.execute("INSERT INTO omnis.principal (principal_id, email, display_name, status) VALUES (%s, %s, %s, 'disabled')",
                   (disabled_actor, f"rule-disabled-{marker}@example.test", "Disabled"))
        db.execute("INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role, status) VALUES (%s, %s, 'reader', 'active')",
                   (tenant_a, disabled_actor))

    rule_id = _attempt_tenant_rule_insert(assistant_rls_dsn, tenant_a, actor_a, actor_a)
    for principal, attributed in ((actor_a, actor_b), (actor_b, actor_b),
                                  (suspended_actor, suspended_actor), (disabled_actor, disabled_actor)):
        with pytest.raises(psycopg.Error):
            _attempt_tenant_rule_insert(assistant_rls_dsn, tenant_a, principal, attributed)

    # DELETE has its own actor-aware USING policy; tenant context alone is insufficient.
    assert _attempt_tenant_rule_delete(assistant_rls_dsn, tenant_a, actor_b, rule_id) == 1
    assert _attempt_tenant_rule_delete(assistant_rls_dsn, tenant_a, suspended_actor, rule_id) == 1
    assert _attempt_tenant_rule_delete(assistant_rls_dsn, tenant_a, disabled_actor, rule_id) == 1
    assert _attempt_tenant_rule_delete(assistant_rls_dsn, tenant_a, actor_a, rule_id) == 0
