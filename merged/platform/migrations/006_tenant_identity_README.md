# OMNIS tenant identity migration

Apply `006_tenant_identity.sql` after migrations 001-005. It creates tenants,
principals, memberships, and per-principal API credentials. The migration does not
create deployment users, tenants, or credentials automatically.

## Credential model

- Issue a unique high-entropy token in the form `omnis_live_<random>` and show it
  to the user once. Never store or log the raw token.
- Store only its HMAC-SHA256 digest in `omnis.api_credential.token_digest`.
  Configure `OMNIS_API_KEY_PEPPER` as a separate secret of at least 32 characters.
- Each request must identify exactly one tenant using `X-OMNIS-Tenant: <tenant UUID>`.
  A credential is accepted only when its principal has an active membership in that
  active tenant and the credential is neither revoked nor expired.
- Roles are `owner`, `admin`, `operator`, `analyst`, and `reader`.
  Role permissions are defined in `omnis/identity.py` and default to least privilege.
- Revoke a credential by setting `revoked_at`; suspend a principal, tenant, or
  membership through its status field. These are administrative operations and must
  be performed by a separate database-owner/provisioning process.

The current gateway's existing `OMNIS_API_TOKEN` remains a legacy single-token
compatibility mechanism. Tenant credentials are currently exposed only through the
`GET /v1/identity/me` identity probe; existing evidence and business routes are
not yet tenant-scoped and must not be exposed to tenant credentials until their storage
queries, idempotency constraints, and audit attribution are tenant-aware. This is an
intentional fail-closed rollout boundary, not a claim that existing ledger rows are
isolated by tenant.

The runtime role needs SELECT on the four identity tables and no mutation rights.
Provision tenants, principals, memberships, and credentials through a separate
trusted provisioning role. Do not grant the runtime role table ownership, INSERT,
UPDATE, DELETE, TRUNCATE, schema CREATE, or migration privileges.
