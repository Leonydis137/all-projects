"""Regression tests for tenant usage quota-policy row-level security."""
from pathlib import Path
import re


MIGRATION = Path(__file__).parents[1] / "migrations" / "014_tenant_usage_policy_member_reads.sql"


def test_quota_policy_is_visible_to_every_active_tenant_member():
    sql = MIGRATION.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE POLICY tenant_usage_policy_scope ON omnis\.tenant_usage_policy\s+"
        r"USING\s*\((.*?)\)\s+WITH CHECK\s*\((.*?)\);",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )

    assert match, "migration must recreate the quota policy RLS policy"
    using, with_check = match.groups()

    # updated_by is audit attribution, not a visibility boundary. Restricting
    # SELECT to the policy editor causes other members to see no quota row.
    assert "updated_by" not in using.lower()
    assert "tenant_membership" in using
    assert "m.status = 'active'" in using
    assert "current_setting('omnis.tenant_id', true)" in using
    assert "current_setting('omnis.principal_id', true)" in using

    assert "tenant_membership" in with_check
    assert "m.status = 'active'" in with_check
