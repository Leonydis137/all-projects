# OMNIS PostgreSQL migrations

Apply migrations in numeric order using a database-owner or migration role before enabling PostgreSQL-backed OMNIS storage:

1. `001_evidence_and_audit.sql` creates the `omnis` schema and ledger tables.
2. `002_ledger_immutability.sql` hardens hash formats, removes default PUBLIC privileges, and blocks UPDATE, DELETE, and TRUNCATE.
3. `003_audit_event_canonical_payload.sql` adds the canonical audit-event body required by the PostgreSQL audit adapter.
4. `004_evidence_idempotency.sql` adds an optional unique client idempotency key and builds its unique index concurrently so normal evidence writes can continue.
5. `005_case_insensitive_source_uri.sql` atomically replaces the original case-sensitive HTTP(S) constraint; it installs the new check as NOT VALID and validates it without blocking ordinary writes.
6. `006_tenant_identity.sql` creates tenants, principals, memberships, and HMAC-digested API credentials.

Example:

```sh
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 001_evidence_and_audit.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 002_ledger_immutability.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 003_audit_event_canonical_payload.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 004_evidence_idempotency.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 005_case_insensitive_source_uri.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 006_tenant_identity.sql
```

Migration 004 intentionally contains `CREATE INDEX CONCURRENTLY` and must not be wrapped in an explicit transaction. If an interrupted concurrent index build leaves an invalid index, inspect `pg_index.indisvalid`, drop that invalid index with `DROP INDEX CONCURRENTLY omnis.evidence_idempotency_key_uq`, and rerun migration 004.

Migration 005 wraps its constraint replacement in one transaction. If validation finds legacy rows with non-HTTP(S) URIs, the transaction rolls back and the original constraint remains in place; clean those rows before retrying.

Set `OMNIS_DATABASE_URL` only after all five migrations have completed. This switches both evidence and audit storage from their local fallback implementations to PostgreSQL. During a rolling deployment, drain old application instances before relying on the durable audit chain; older instances do not write to PostgreSQL.

## Application-role provisioning

The migrations deliberately do not create or guess deployment roles. Provision a dedicated non-owner application role through your deployment's secret and role-management process. Grant only the operations the application needs, for example:

```sql
GRANT USAGE ON SCHEMA omnis TO omnis_app;
GRANT SELECT, INSERT ON omnis.evidence TO omnis_app;
GRANT USAGE, SELECT ON SEQUENCE omnis.evidence_sequence_seq TO omnis_app;
GRANT SELECT, INSERT ON omnis.audit_event TO omnis_app;
GRANT USAGE, SELECT ON SEQUENCE omnis.audit_event_sequence_seq TO omnis_app;
```

Do not grant table ownership, UPDATE, DELETE, TRUNCATE, schema CREATE, or migration privileges to the runtime role. Confirm the generated sequence names in the target database before applying grants. The database owner and superusers can still bypass ordinary application protections; use separate ownership and runtime roles.

Migration 003 leaves `event_json` nullable to permit schema rollout over databases with existing audit rows. Existing rows without canonical bodies deliberately fail closed during full audit verification; reconcile or migrate those records before enabling PostgreSQL audit mode.

After migration 006, grant the runtime role read-only access to identity records: `GRANT SELECT ON omnis.tenant, omnis.principal, omnis.tenant_membership, omnis.api_credential TO omnis_app;`. Do not grant identity-table mutation privileges to the runtime role. The tenant credential lookup is used only by `GET /v1/identity/me`; existing business routes still use the legacy shared token until tenant-scoped data access is implemented.

The application uses a lightweight latest-event audit health probe. Full-chain integrity verification remains available through the audit verification operation and should be run as a deliberate integrity check rather than on every load-balancer probe. Hash chains do not prove source authenticity or actor identity, and cannot detect deletion of a final suffix without an independently retained checkpoint.


## Initial tenant provisioning

Use a separate database-owner connection for provisioning; do not give these privileges
to the runtime role. Configure `OMNIS_PROVISIONING_DATABASE_URL` and the same
`OMNIS_API_KEY_PEPPER` used by the runtime, then run:

```sh
cd merged/platform
python -m omnis.provision_identity \
  --slug example-tenant \
  --tenant-name "Example Tenant" \
  --email owner@example.com \
  --display-name "Tenant Owner"
```

The command creates a tenant, its initial owner principal and membership, and one
API credential in a single transaction. It prints the raw bearer token once after
commit; copy it directly into a secret manager. The database stores only its keyed
digest. If the command fails, it does not print the token. The provisioning DSN
must use a separate owner/provisioning role and must never be configured as the
application's `OMNIS_DATABASE_URL`.
