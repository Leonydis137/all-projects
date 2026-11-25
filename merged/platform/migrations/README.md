# OMNIS PostgreSQL migrations

Apply migrations in numeric order using a database-owner or migration role before enabling PostgreSQL-backed OMNIS storage:

1. `001_evidence_and_audit.sql` creates the `omnis` schema and ledger tables.
2. `002_ledger_immutability.sql` hardens hash formats, removes default PUBLIC privileges, and blocks UPDATE, DELETE, and TRUNCATE.
3. `003_audit_event_canonical_payload.sql` adds the canonical audit-event body required by the PostgreSQL audit adapter.
4. `004_evidence_idempotency.sql` adds an optional unique client idempotency key and builds its unique index concurrently so normal evidence writes can continue.
5. `005_case_insensitive_source_uri.sql` atomically replaces the original case-sensitive HTTP(S) constraint; it installs the new check as NOT VALID and validates it without blocking ordinary writes.
6. `006_tenant_identity.sql` creates tenants, principals, memberships, and HMAC-digested API credentials.
7. `007_tenant_evidence.sql` creates a per-tenant append-only evidence ledger with forced row-level security, per-tenant idempotency, and tenant-local hash chains.
8. `008_identity_row_security.sql` enforces transaction-local tenant row security on tenant, membership, and API credential tables.
9. `009_tenant_bound_credentials.sql` binds every API credential to one tenant, safely backfills unambiguous legacy credentials, and updates the RLS policy.
10. `010_tenant_audit.sql` creates an independent append-only audit chain per tenant with forced RLS.
11. `011_tenant_decision_rules.sql` adds tenant-owned decision rules with forced RLS and principal attribution.
12. `012_tenant_assistant_conversations.sql` adds tenant-isolated assistant conversations and message history with forced RLS.
13. `013_tenant_usage_metering.sql` adds tenant usage events, rolling-minute counters, and configurable monthly request quotas with forced RLS.
14. `014_tenant_usage_policy_member_reads.sql` fixes quota-policy visibility so every active member can read the tenant's configured limit; policy ownership remains audit metadata, not a read restriction.
15. `015_tenant_audit_active_actor.sql` requires every tenant audit insert to be attributed to the transaction's authenticated principal, with active membership, principal, and tenant status.
16. `016_tenant_evidence_and_rules_active_actor.sql` binds tenant evidence submissions and decision-rule mutations to the transaction principal, requiring active membership, principal, and tenant status.
17. `017_tenant_lifecycle_storage_rls.sql` requires active tenant/principal/membership state for assistant and usage operations, makes message and usage-event history append-only, and separates credential read, issue, and revocation policies.

Example:

```sh
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 001_evidence_and_audit.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 002_ledger_immutability.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 003_audit_event_canonical_payload.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 004_evidence_idempotency.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 005_case_insensitive_source_uri.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 006_tenant_identity.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 007_tenant_evidence.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 008_identity_row_security.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 009_tenant_bound_credentials.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 010_tenant_audit.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 011_tenant_decision_rules.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 012_tenant_assistant_conversations.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 013_tenant_usage_metering.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 014_tenant_usage_policy_member_reads.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 015_tenant_audit_active_actor.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 016_tenant_evidence_and_rules_active_actor.sql
psql "$OMNIS_DATABASE_URL" -v ON_ERROR_STOP=1 -f 017_tenant_lifecycle_storage_rls.sql
```

Migration 004 intentionally contains `CREATE INDEX CONCURRENTLY` and must not be wrapped in an explicit transaction. If an interrupted concurrent index build leaves an invalid index, inspect `pg_index.indisvalid`, drop that invalid index with `DROP INDEX CONCURRENTLY omnis.evidence_idempotency_key_uq`, and rerun migration 004.

Migration 005 wraps its constraint replacement in one transaction. If validation finds legacy rows with non-HTTP(S) URIs, the transaction rolls back and the original constraint remains in place; clean those rows before retrying.

Set `OMNIS_DATABASE_URL` only after all seventeen migrations have completed. This switches both evidence and audit storage from their local fallback implementations to PostgreSQL. During a rolling deployment, drain old application instances before relying on the durable audit chain; older instances do not write to PostgreSQL.

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

After migrations 006-017, grant the non-owner runtime role only the operations required by the application:

```sql
GRANT SELECT ON omnis.tenant TO omnis_app;
GRANT SELECT, INSERT, UPDATE ON omnis.tenant_membership TO omnis_app;
GRANT SELECT, INSERT ON omnis.api_credential TO omnis_app;
GRANT UPDATE (revoked_at) ON omnis.api_credential TO omnis_app;
GRANT SELECT, INSERT, UPDATE ON omnis.principal TO omnis_app;
GRANT SELECT, INSERT ON omnis.tenant_evidence TO omnis_app;
GRANT USAGE, SELECT ON SEQUENCE omnis.tenant_evidence_sequence_seq TO omnis_app;
GRANT SELECT, INSERT ON omnis.tenant_audit_event TO omnis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON omnis.tenant_decision_rule TO omnis_app;
GRANT SELECT, INSERT ON omnis.tenant_assistant_conversation TO omnis_app;
GRANT UPDATE (message_count, updated_at) ON omnis.tenant_assistant_conversation TO omnis_app;
GRANT SELECT, INSERT ON omnis.tenant_assistant_message TO omnis_app;
GRANT SELECT ON omnis.tenant_usage_policy TO omnis_app;
GRANT SELECT, INSERT, UPDATE ON omnis.tenant_usage_minute TO omnis_app;
GRANT SELECT, INSERT ON omnis.tenant_usage_event TO omnis_app;
```

Do not grant DELETE, TRUNCATE, ownership, schema CREATE, or BYPASSRLS. Migration
008 enables and forces RLS on `tenant`, `tenant_membership`, and
`api_credential`; migration 009 binds each credential row to its issuing tenant. Each identity/admin transaction must set the transaction-local
`omnis.tenant_id`; authentication sets it before credential lookup. The API
credential policy permits visibility only where its principal has a membership in
the selected tenant. The `principal` table is a shared global identity directory
keyed by normalized email and is intentionally not tenant-filtered at the SQL layer;
application queries must not expose the global directory. Tenant evidence and tenant audit events also
use forced RLS and the same transaction-local tenant context. The tenant audit table
has no global sequence: each tenant has its own event index and predecessor chain.
Append-only evidence, audit, assistant-message, and usage-event tables receive no
runtime UPDATE or DELETE grant; mutable operational tables receive only the
specific UPDATE privileges listed above. Do not broaden credential updates beyond
`revoked_at`. The provisioning
command sets the tenant context before creating the tenant, membership, and initial
credential, then sets the new owner's principal context before credential issuance.
A separate provisioning role does not need BYPASSRLS.

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


## Tenant administration and source acquisition

Tenant credentials may also use the following tenant-aware endpoints:

- `GET /v1/tenant/admin/overview` — owner-only consolidated tenant, membership, and credential counts (tenant:manage; no credential secrets returned).
- `GET /v1/tenant/members` — list memberships in the selected tenant (members:manage).
- `POST /v1/tenant/members` — add or reactivate a member by email (members:manage).
- `PATCH /v1/tenant/members/{principal_id}` — change role or suspend/reactivate membership (members:manage).
- `GET /v1/tenant/credentials` — list credential metadata for the selected tenant (credentials:manage; raw secrets are never returned).
- `POST /v1/tenant/credentials` — issue a credential for an active tenant member (credentials:manage).
- `DELETE /v1/tenant/credentials/{credential_id}` — revoke a credential in the selected tenant (credentials:manage).
- `GET /v1/tenant/source/attestation-key` — retrieve the public fetch-attestation key.
- `POST /v1/tenant/source/fetch` — run COVENANT authorization before controlled source acquisition and append the signed observation to the tenant evidence ledger.
- `POST /v1/tenant/govern` — evaluate a COVENANT-governed action and record the decision in the tenant audit chain.
- `GET /v1/tenant/audit` — list only this tenant's audit events (audit:read).
- `GET /v1/tenant/audit/verify` — verify the complete tenant-local audit chain (audit:read).

New credentials are returned once in the issuing response and must be copied to a
secret manager. They expire after 1-365 days (90 by default). Membership operations
are audited in the same PostgreSQL transaction. The store serializes membership
changes per tenant and prevents demoting or suspending its last active owner. Only
an owner may assign the owner role. The runtime role needs INSERT/UPDATE privileges
on membership, principal and credential tables as shown above; RLS and explicit
tenant predicates constrain tenant and credential visibility.


Migration 009 binds credentials to the tenant in which they were issued.
Existing credentials are automatically backfilled only when their principal has
exactly one membership. Before applying it, inspect ambiguous credentials:

```sql
SELECT c.credential_id, c.principal_id, count(m.tenant_id) AS memberships
FROM omnis.api_credential c
LEFT JOIN omnis.tenant_membership m ON m.principal_id = c.principal_id
GROUP BY c.credential_id, c.principal_id
HAVING count(m.tenant_id) <> 1;
```

A principal-level token from the previous schema could authenticate against every
tenant where that principal had a membership. Therefore credentials with zero or
multiple memberships cannot be safely assigned automatically. Revoke/delete those
legacy credential rows after reviewing the report, then apply migration 009 and
issue new tenant-bound credentials. Do not reuse one legacy token across tenants.
After migration 009, every remaining credential is bound to one tenant and cannot
authenticate against another tenant even if the principal belongs to both.


## Tenant usage metering and limits

Apply migration `013_tenant_usage_metering.sql` after migration 012. Tenant assistant
message submissions are recorded as one request unit before provider execution.
Provider token usage is not inferred or fabricated; token-level metering can be added
when the provider adapter exposes verified usage metadata.

The rolling-minute rate limit defaults to 30 assistant requests per tenant per minute.
Set `OMNIS_TENANT_ASSISTANT_RPM` to a positive integer to change the platform limit.
Rate-limit attempts are recorded as rejected usage events and return HTTP 429 before
the provider is called. The counter and usage event are committed with the tenant audit
event in one transaction.

Monthly quotas are explicit per-tenant policy rows. No policy row, or a NULL limit,
means unlimited monthly assistant requests; a limit of zero blocks all assistant
requests. Configure a tenant quota using a database-owner connection:

```sql
BEGIN;
SELECT set_config('omnis.tenant_id', '<tenant-uuid>', true);
SELECT set_config('omnis.principal_id', '<owner-principal-uuid>', true);
INSERT INTO omnis.tenant_usage_policy (tenant_id, monthly_request_limit, updated_by)
VALUES ('<tenant-uuid>', 10000, '<owner-principal-uuid>')
ON CONFLICT (tenant_id) DO UPDATE
SET monthly_request_limit = EXCLUDED.monthly_request_limit,
    updated_by = EXCLUDED.updated_by,
    updated_at = now();
COMMIT;
```

The runtime role can read but cannot modify quota policy. Monthly quota rejections
are persisted and return HTTP 429. `GET /v1/tenant/usage` returns the selected
tenant's current calendar-month usage summary and requires `usage:read`. Usage
events, minute counters, and policy reads are protected by forced RLS.
