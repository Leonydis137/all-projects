# OMNIS PostgreSQL migrations

Apply migrations in numeric order using a database-owner or migration role:

1. `001_evidence_and_audit.sql` creates the `omnis` schema and ledger tables.
2. `002_ledger_immutability.sql` hardens hash formats, removes default PUBLIC privileges, and blocks UPDATE, DELETE, and TRUNCATE.

Example:

```sh
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 001_evidence_and_audit.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 002_ledger_immutability.sql
```

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

The schema is a future durable-storage foundation. The current OMNIS API still uses its SQLite evidence ledger and in-process audit log; these migrations do not silently switch runtime storage. Hash chains detect record modification relative to the retained chain, but do not prove source authenticity, actor identity, or detect deletion of an entire suffix without an independently retained checkpoint.
