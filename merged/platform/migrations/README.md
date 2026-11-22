# OMNIS PostgreSQL migrations

Apply migrations in numeric order using a database-owner or migration role before enabling PostgreSQL-backed OMNIS storage:

1. `001_evidence_and_audit.sql` creates the `omnis` schema and ledger tables.
2. `002_ledger_immutability.sql` hardens hash formats, removes default PUBLIC privileges, and blocks UPDATE, DELETE, and TRUNCATE.
3. `003_audit_event_canonical_payload.sql` adds the canonical audit-event body required by the PostgreSQL audit adapter.
4. `004_evidence_idempotency.sql` adds an optional unique client idempotency key for retry-safe evidence submission.
5. `005_case_insensitive_source_uri.sql` replaces the original case-sensitive HTTP(S) constraint on existing databases.

Example:

```sh
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 001_evidence_and_audit.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 002_ledger_immutability.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 003_audit_event_canonical_payload.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 004_evidence_idempotency.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 005_case_insensitive_source_uri.sql
```

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

The application uses a lightweight latest-event audit health probe. Full-chain integrity verification remains available through the audit verification operation and should be run as a deliberate integrity check rather than on every load-balancer probe. Hash chains do not prove source authenticity or actor identity, and cannot detect deletion of a final suffix without an independently retained checkpoint.
