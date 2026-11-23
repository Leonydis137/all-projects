"""Provision the first OMNIS tenant owner using a separate database-owner role.

The generated bearer token is printed once after the transaction commits. Only its
HMAC-SHA256 digest is stored. Never redirect the token to logs or commit it.
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import sys
from uuid import uuid4

from .identity import digest_api_key


_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


def _required_env(name: str, minimum: int = 1) -> str:
    value = os.environ.get(name, "")
    if len(value) < minimum:
        raise SystemExit(f"{name} must be configured (minimum {minimum} characters)")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an OMNIS tenant and its initial owner credential.")
    parser.add_argument("--slug", required=True, help="lowercase tenant slug")
    parser.add_argument("--tenant-name", required=True, help="tenant display name")
    parser.add_argument("--email", required=True, help="owner email address")
    parser.add_argument("--display-name", required=True, help="owner display name")
    parser.add_argument("--label", default="initial-owner", help="credential label")
    args = parser.parse_args()

    slug = args.slug.strip()
    tenant_name = args.tenant_name.strip()
    email = args.email.strip().lower()
    display_name = args.display_name.strip()
    label = args.label.strip()
    if not _SLUG.fullmatch(slug):
        raise SystemExit("--slug must be 2-63 lowercase letters, digits, or hyphens and start with a letter or digit")
    if not 1 <= len(tenant_name) <= 160 or not 1 <= len(display_name) <= 160:
        raise SystemExit("tenant and owner display names must contain 1-160 characters")
    if not 3 <= len(email) <= 320 or "@" not in email:
        raise SystemExit("--email must be a valid-looking address of 3-320 characters")
    if not 1 <= len(label) <= 100:
        raise SystemExit("--label must contain 1-100 characters")

    dsn = _required_env("OMNIS_PROVISIONING_DATABASE_URL")
    pepper = _required_env("OMNIS_API_KEY_PEPPER", 32)
    token = "omnis_live_" + secrets.token_urlsafe(32)
    digest = digest_api_key(token, pepper)
    try:
        from psycopg.rows import dict_row
        from .postgres_connection import connect_postgres
        with connect_postgres(dsn, dict_row, statement_timeout_ms=10_000) as db:
            with db.cursor() as cur:
                tenant_id = str(uuid4())
                cur.execute("SELECT set_config('omnis.tenant_id', %s, true)", (tenant_id,))
                cur.execute(
                    "INSERT INTO omnis.tenant (tenant_id, slug, display_name) VALUES (%s, %s, %s)",
                    (tenant_id, slug, tenant_name),
                )
                cur.execute(
                    "INSERT INTO omnis.principal (email, display_name) VALUES (%s, %s) RETURNING principal_id",
                    (email, display_name),
                )
                principal_id = str(cur.fetchone()["principal_id"])
                cur.execute(
                    """INSERT INTO omnis.tenant_membership (tenant_id, principal_id, role)
                       VALUES (%s, %s, 'owner')""",
                    (tenant_id, principal_id),
                )
                cur.execute(
                    """INSERT INTO omnis.api_credential
                       (principal_id, token_prefix, token_digest, label)
                       VALUES (%s, %s, %s, %s)""",
                    (principal_id, token[:32], digest, label),
                )
        # Print only after the transaction has committed successfully.
        import json
        print(json.dumps({
            "tenant_id": tenant_id,
            "principal_id": principal_id,
            "email": email,
            "tenant_header": tenant_id,
            "api_token_once": token,
        }, indent=2))
        return 0
    except Exception as exc:
        # Do not include the token or database DSN in diagnostics.
        print(f"Tenant provisioning failed: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
