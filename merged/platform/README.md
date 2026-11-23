# OMNIS - all projects, one platform

Author: Juan-Louw Greyling

OMNIS is the integration gateway for this monorepo. The original projects remain under
`merged/sources/`; the platform exposes selected capabilities through versioned APIs.
A catalogue entry is not a claim that a project is fully integrated or production-ready.

## Current gateway capabilities

- COVENANT policy evaluation and governed decision routes.
- AEON protocol endpoint and decision rules.
- Project inventory and source catalogue.
- Statistical and mathematical endpoints.
- Optional external-model assistant (requires an explicitly configured provider key).
- Append-only evidence ledger with hash-chain verification.
- Tamper-evident audit events for the lifecycle of all `/v1/` requests except the
  read-only `/v1/audit` endpoint. The request log records method, path, and response
  status only; request bodies, credentials, and query strings are not copied into it.
- SQLite remains the default evidence store; PostgreSQL is selected only when
  `OMNIS_DATABASE_URL` is explicitly configured.

## Run

```bash
cd merged/platform
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn omnis.api:app --host 127.0.0.1 --port 8080
```

Set `OMNIS_API_TOKEN` to protect API routes. Without `OMNIS_DATABASE_URL`, OMNIS uses
the persistent SQLite database selected by `OMNIS_EVIDENCE_DB`. To use PostgreSQL,
apply migrations 001 through 013 in order using a database-owner/migration role, then set `OMNIS_DATABASE_URL` to a PostgreSQL
DSN for a dedicated runtime role with schema USAGE and SELECT/INSERT privileges only.
Remote connections require certificate and hostname verification (`sslmode=verify-full`);
configure the provider CA as the libpq root certificate. The runtime never runs schema
migrations automatically. Set `OMNIS_DB_VERIFY_TIMEOUT_MS` to control the full-chain
verification statement timeout (default 300000 ms); routine health probes remain bounded
by the 10000 ms query timeout. Export and verify existing SQLite evidence before switching;
setting the PostgreSQL URL does not automatically copy the SQLite records. Supply an optional
`idempotency_key` on evidence submissions to make client retries return the original row;
reusing a key with different record content is rejected.

PostgreSQL adapter integration tests run when `OMNIS_TEST_DATABASE_URL` is set.
The API reports unavailable integrations honestly; it does not substitute fabricated
data when credentials or source systems are absent.

Both evidence and audit events use PostgreSQL when `OMNIS_DATABASE_URL` is configured.
The evidence insert and its corresponding audit event share one transaction, so an
audit failure rolls back the evidence insert. Optional client idempotency keys make
evidence retries safe; reusing a key with different content is rejected.

For every `/v1/` request except the read-only audit endpoint, OMNIS writes a
`http.request.started` event before route dispatch. If that write fails, the request
is rejected with HTTP 503 before the route executes. A completion event records the
response status. If completion logging fails after an action has run, the response is
preserved and marked with `X-OMNIS-Audit-Status: incomplete`; clients must not assume
that the operation was rolled back. Authentication failures are included in the request
lifecycle log. Request bodies and bearer tokens are never included.

Health probes validate the latest ledger entries without scanning full history.
Use the explicit evidence and audit verification operations for full-chain checks.
Hash integrity does not prove source authenticity or actor identity and cannot
independently detect deletion of a final suffix without an external checkpoint.
Existing SQLite evidence and in-memory audit history are not automatically migrated;
export, import, and verify historical records before switching storage.

## Controlled source acquisition

The authenticated `POST /v1/source/fetch` endpoint retrieves one source and appends
its SHA-256 digest plus a signed fetch-observation attestation to the evidence ledger.
The fetched body is held in memory only and is not persisted by this connector.
`GET /v1/source/attestation-key` returns the Ed25519 public key and its SHA-256
fingerprint. Consumers must pin that fingerprint through an independent channel;
trusting a public key solely because the same API returned it is not sufficient.

Configure both environment variables before enabling the connector:

- `OMNIS_SOURCE_ALLOWLIST`: comma-separated exact hostnames (IDNA-normalized); no
  wildcard or suffix matching.
- `OMNIS_PROVENANCE_PRIVATE_KEY_B64`: secret-store value containing a base64url
  encoded 32-byte Ed25519 private key. Never commit this value or ship it to clients.
- `OMNIS_SOURCE_FETCHER_ID`: optional stable service identity (default
  `omnis-source-fetcher`).

Outbound policy is deliberately restrictive: HTTPS only, port 443 only, exact
allowlisted hostname, no URL credentials, query string or fragment, no IP-literal
hosts, no redirects, TLS certificate/hostname verification, DNS resolution checked
for public IP addresses and the selected IP pinned for the actual socket connection.
Responses using content encoding are rejected, the response is limited to 2 MiB, and
the HTTP connection/read timeout is 8 seconds (DNS resolution follows the operating system resolver's timeout policy). No proxy environment variable or caller-supplied
header is used.

Each stored attestation signs a canonical statement containing the source URI,
acquisition time, content digest and length, media type, fetcher identity, selected
public IP, checked DNS answers, and the no-redirect/TLS-verification observations.
The signature is verified before the record is accepted and the attestation is
included in the evidence hash-chain commitment for both SQLite and PostgreSQL.

**Important trust boundary:** this is a platform-signed observation that OMNIS fetched
these bytes over verified HTTPS from an allowlisted host. It is not a publisher
signature, does not prove the publisher's identity beyond TLS hostname validation,
does not validate the source's claims, and does not establish the licence asserted
by the caller. The evidence record therefore continues to report
`source_authenticity: unverified` / `not_established`. Pin the signing-key fingerprint
out-of-band and manage key rotation as an explicit trust change.


## Tenant identity foundation

Migrations `006_tenant_identity.sql` and `008_identity_row_security.sql` add PostgreSQL tenants, principals, active
memberships, role assignments, revocable API credentials, and forced tenant RLS. Migration
`009_tenant_bound_credentials.sql` binds each credential to exactly one tenant. Tenant credentials
are high-entropy `omnis_live_...` tokens; only keyed HMAC-SHA256 digests are stored.
Set `OMNIS_API_KEY_PEPPER` to a separate secret containing at least 32 characters.
The authenticated identity, membership administration, credential lifecycle, tenant evidence, tenant audit, tenant governance, and tenant source acquisition routes require both a tenant credential and an explicit `X-OMNIS-Tenant` UUID header. Tenant operations are role-gated, row-level secured where supported by PostgreSQL, and audited against the authenticated principal ID.

This is a staged rollout: tenant credentials are accepted only by `/v1/identity/me`, explicitly tenant-aware `/v1/tenant/*` routes, and `/v1/tenant/source/*`. The legacy global evidence, governance, and other business endpoints continue to use `OMNIS_API_TOKEN`; they are not tenant-isolated. Do not expose tenant credentials to those routes until their storage, idempotency, authorization, and audit queries enforce tenant boundaries. The migrations create no users, tenants, or credentials automatically; provision
them through a separate trusted provisioning connection. The runtime role receives
only the explicit table privileges documented in `migrations/README.md`; forced RLS
is enabled for tenant, membership, credential, and tenant-evidence rows.


To create the first tenant and owner credential, use the separate owner-only
`OMNIS_PROVISIONING_DATABASE_URL` with `python -m omnis.provision_identity`.
The command prints the generated API token once after commit; store it in a secret
manager immediately. Never use the provisioning DSN as the runtime database URL.


## Tenant-scoped evidence API

After applying migrations 006 through 010, tenant credentials can use:

- `POST /v1/tenant/evidence` — append evidence as the authenticated principal.
- `GET /v1/tenant/evidence` — list only the selected tenant's evidence.
- `GET /v1/tenant/evidence/verify` — verify that tenant's hash chain.

Send the tenant UUID in `X-OMNIS-Tenant`. The role must include
`evidence:write` for append or `evidence:read` for list/verify. The API assigns
`submitted_by` from the authenticated principal; clients cannot spoof the actor.
The table has forced PostgreSQL row-level security, tenant-specific idempotency
keys, independent hash chains, and append-only triggers. Each operation records
the authenticated principal as the audit actor.

The existing global `/v1/evidence` routes remain on the legacy shared-token path.
They are not transparently migrated or exposed through tenant credentials.


## Tenant administration and source acquisition

After migrations 006-010, tenant owners and admins can manage memberships and API
credentials using tenant credentials:

- `GET /v1/tenant/members` — list memberships.
- `POST /v1/tenant/members` — add or reactivate a member by email.
- `PATCH /v1/tenant/members/{principal_id}` — change role or suspend/reactivate membership.
- `POST /v1/tenant/credentials` — issue a credential for an active member.
- `DELETE /v1/tenant/credentials/{credential_id}` — revoke a credential.

Only owners may assign the owner role, modify an existing owner's membership, or issue/revoke another owner's credentials.
The database transaction serializes membership changes and prevents demoting or
suspending the last active owner. New credentials expire after 1-365 days (90 by
default), are bound to one tenant, stored only as keyed digests, and returned once to the issuer. Suspending a membership revokes all active credentials for that tenant membership; reactivation requires a newly issued token.

Tenant audit and governance are available through `GET /v1/tenant/audit`, `GET /v1/tenant/audit/verify`, and `POST /v1/tenant/govern`. Each tenant has an independent append-only audit chain, protected by forced RLS and a tenant-local event index. Authenticated tenant request lifecycle events and tenant mutations are written to that chain; they are not copied into the global audit chain. The legacy global audit chain remains the operational audit for non-tenant requests. Only owner, admin, and analyst roles receive `audit:read`.

Tenant-aware source acquisition is available through `POST /v1/tenant/source/fetch`.
COVENANT authorization runs before network access; the resulting signed fetch
observation is appended to the authenticated tenant's evidence ledger. Retrieve
the verification key using `GET /v1/tenant/source/attestation-key`. This proves
what the configured fetcher observed, not publisher authenticity or claim truth.

## Tenant-governed platform operations

Tenant credentials can execute the stateless OMNIS capabilities through dedicated
routes. Each route requires `governance:execute`, evaluates the action through
COVENANT, and records the authenticated principal and decision in that tenant's
audit chain:

- `POST /v1/tenant/decide` — run a fresh default decision engine per request; the
  supplied decision context is passed into COVENANT evaluation.
- `POST /v1/tenant/recommend` — fit and query an in-request recommender without
  persisting tenant data or shared model state.
- `POST /v1/tenant/protocols/respond` — generate an AEON response from a fresh
  per-request protocol engine, isolated from legacy feedback mutations.
- `POST /v1/tenant/stats/ab` and `POST /v1/tenant/stats/posterior` — run statistical
  analysis with the same input validation as the legacy endpoints.
- `POST /v1/tenant/math/gcd-lcm` — run the stateless number-theory helper.

These routes do not make the legacy `/v1/*` endpoints tenant-aware. Global
catalogue, rule mutation, evidence, assistant, and other legacy routes continue
to require the shared `OMNIS_API_TOKEN` until their own data and state boundaries
are tenant-safe. Tenant operations are audited separately; they are never written
to the global audit chain.


## Tenant-specific decision rules

Apply migration `011_tenant_decision_rules.sql` and grant the runtime role the
explicit privileges documented in `migrations/README.md`. Tenant credentials can
then use `GET/POST /v1/tenant/decision-rules`, `PUT /v1/tenant/decision-rules/{rule_id}`,
and `DELETE /v1/tenant/decision-rules/{rule_id}`. Owners and admins can manage
rules; operator, analyst, and reader roles can inspect them. Rule mutations pass
COVENANT and are committed with their principal-attributed audit event in the same
database transaction. The tenant decision endpoint evaluates that tenant's enabled
rules in priority order alongside the platform defaults. PostgreSQL forced RLS and
the explicit tenant predicate prevent cross-tenant rule access. The legacy global
`/v1/decision/rules` API remains behind the shared token and is not tenant-aware.


## Tenant-isolated assistant conversations

Migration `012_tenant_assistant_conversations.sql` creates tenant-scoped conversation
metadata and append-only message history with forced RLS. Apply it before enabling
the tenant assistant endpoints. Tenant credentials can list and create conversations
and send messages through `POST /v1/tenant/assistant/conversations/{conversation_id}/messages`.
The server loads history from the selected tenant's database rows; client-supplied
history is not accepted. Every conversation and exchange is attributed to the
authenticated principal and tenant audit chain. The provider call uses the configured
OMNIS Anthropic account key; tenant data is isolated in storage and request context,
but provider billing and credentials remain platform-managed. Message content is sent to the configured Anthropic API for generation; apply the provider's data-processing and retention terms to tenant deployments.


## Tenant usage metering and limits

Tenant assistant message submissions are metered as one request unit and recorded
before provider execution in a tenant-isolated PostgreSQL usage ledger. A rolling
per-tenant minute counter enforces the configurable `OMNIS_TENANT_ASSISTANT_RPM`
limit (30 requests/minute by default). Rejected attempts are retained as usage events
and return HTTP 429 without calling the assistant provider.

Monthly request quotas are configured per tenant by a database owner through
`omnis.tenant_usage_policy`; an absent policy or NULL limit is unlimited. The
runtime role cannot change quota policy. Tenant members with `usage:read` can
retrieve the current calendar-month summary from `GET /v1/tenant/usage`.
Metering currently counts assistant requests, not provider tokens or monetary cost.
Apply migration 013 and the runtime grants documented in `migrations/README.md`.


## Unified tenant console

The root console at `/` now includes a tenant workspace alongside the legacy
single-token tools. Open the **Tenant** tab and provide a tenant-bound
`omnis_live_...` credential and the matching tenant UUID. The console validates
the credential through `GET /v1/identity/me` and uses the authenticated
permissions to show available tenant functions.

The tenant workspace provides:

- Tenant identity and role/permission visibility.
- Membership administration: add/reactivate members, change roles, and suspend/reactivate access when permitted.
- Credential lifecycle: issue expiring tenant-bound credentials, inspect metadata, and revoke credentials; raw tokens are shown once only.
- Current-month request usage and configured monthly quota.
- Tenant evidence listing and ledger verification (when permitted).
- Tenant audit event listing and hash-chain verification (when permitted).
- Tenant decision-rule listing, creation, and deletion (when permitted).
- COVENANT-governed tenant decision and AEON protocol operations (when permitted).
- Tenant assistant conversation creation, history retrieval, and messaging.

### Tenant onboarding and administration dashboard

Provision a new tenant through the trusted provisioning command in
`migrations/README.md`; tenant creation is deliberately not exposed as a
tenant-member API. The provisioning database URL must use a separate owner role
and must never be configured as the runtime database URL.

After provisioning:

1. Store the one-time owner bearer token in an approved secret manager and retain
   the tenant UUID alongside it. The console does not persist either value.
2. Connect through the Tenant tab and confirm the tenant identity and owner role.
3. Add members using their normalized email address and assign least-privilege roles.
4. Issue a separate expiring credential to each active member; deliver it securely.
5. Verify that at least one active owner remains and review credential expiry and
   revocation regularly.

Owners can view the consolidated administration dashboard through
`GET /v1/tenant/admin/overview` (permission: `tenant:manage`). It reports tenant
status, membership totals, active owners, and credential totals without returning
credential secrets or digests. The dashboard includes an onboarding checklist.
Membership and credential mutations remain on the existing permission-gated routes
and are audited in the tenant-local audit chain.

Assistant conversation history is retrieved from the tenant-scoped PostgreSQL
store; the browser does not inject or persist conversation history. Credentials
are held in page memory only and are cleared when **Disconnect** is selected or
the page is reloaded. Do not paste tenant credentials into the legacy global API
token field. The tenant console calls only explicitly tenant-aware API routes.

`GET /v1/tenant/assistant/conversations/{conversation_id}` returns one tenant's
conversation metadata and up to 100 stored messages, subject to the authenticated
tenant membership and `assistant:use` permission.
