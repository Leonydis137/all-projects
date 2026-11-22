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
apply migrations 001 through 005 in order using a database-owner/migration role, then set `OMNIS_DATABASE_URL` to a PostgreSQL
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

Migration `006_tenant_identity.sql` adds PostgreSQL tenants, principals, active
memberships, role assignments, and revocable API credentials. Tenant credentials
are high-entropy `omnis_live_...` tokens; only keyed HMAC-SHA256 digests are stored.
Set `OMNIS_API_KEY_PEPPER` to a separate secret containing at least 32 characters.
The authenticated `GET /v1/identity/me` probe and tenant evidence routes require both
a tenant credential and an explicit `X-OMNIS-Tenant` UUID header. Tenant evidence
operations are role-gated, row-level secured, and audited against the authenticated
principal ID.

This is a staged rollout: tenant credentials are accepted by the identity probe and
the dedicated `/v1/tenant/evidence` endpoints only. The legacy global evidence,
governance, and other business endpoints continue to use `OMNIS_API_TOKEN`; they are
not tenant-isolated. Do not expose tenant credentials to those routes until their
storage, idempotency, authorization, and audit queries enforce tenant boundaries. The migration creates no users,
tenants, or credentials automatically; provision them through a separate trusted
database-owner process. The runtime database role receives SELECT-only access to
identity tables.


To create the first tenant and owner credential, use the separate owner-only
`OMNIS_PROVISIONING_DATABASE_URL` with `python -m omnis.provision_identity`.
The command prints the generated API token once after commit; store it in a secret
manager immediately. Never use the provisioning DSN as the runtime database URL.


## Tenant-scoped evidence API

After applying migrations 006 and 007, tenant credentials can use:

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
