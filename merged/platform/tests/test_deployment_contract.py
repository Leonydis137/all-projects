from pathlib import Path
import re


PLATFORM = Path(__file__).resolve().parents[1]
MIGRATIONS = PLATFORM / "migrations"


def test_migration_guide_covers_every_migration_and_command():
    guide = (MIGRATIONS / "README.md").read_text(encoding="utf-8")
    migration_files = sorted(
        path.name for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")
    )
    assert migration_files
    for filename in migration_files:
        assert f"`{filename}`" in guide, f"missing migration description: {filename}"
        assert f"-f {filename}" in guide, f"missing migration command: {filename}"


def test_runtime_credential_grant_is_revocation_only():
    guide = (MIGRATIONS / "README.md").read_text(encoding="utf-8")
    assert "GRANT UPDATE (revoked_at) ON omnis.api_credential TO omnis_app;" in guide
    assert not re.search(
        r"GRANT\s+[^;]*UPDATE[^;]*ON\s+omnis\.tenant_membership\s*,\s*omnis\.api_credential",
        guide,
        flags=re.IGNORECASE,
    )


def test_container_defaults_to_non_root_and_loopback_publishing():
    dockerfile = (PLATFORM / "Dockerfile").read_text(encoding="utf-8")
    compose = (PLATFORM / "docker-compose.yml").read_text(encoding="utf-8")
    assert "USER 10001:10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "${OMNIS_BIND_ADDRESS:-127.0.0.1}:8080:8080" in compose
    assert "read_only: true" in compose
    assert "cap_drop:" in compose and "- ALL" in compose
    assert "no-new-privileges:true" in compose
