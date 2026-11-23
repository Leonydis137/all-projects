# OMNIS architecture
Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>

```
merged/
├── sources/    verbatim copy of every project (never edited - originals stay runnable)
└── platform/   the new combined project
    └── omnis/
        ├── api.py          FastAPI gateway - single entry point, serves the console
        ├── governance.py   COVENANT commandments (imported from sources/services/covenant)
        ├── audit.py        hash-chained audit log of every governed call
        ├── decision.py     data-driven rule engine   (generalises services/autonomous-ai)
        ├── protocols.py    adaptive protocols, no Tk (generalises services/aeon-engine)
        ├── recommend.py    k-NN recommender, numpy only (from services/autonomous-ai)
        ├── stats.py        Bayesian A/B + analyzers (from research/circuit-lower-bounds)
        ├── mathops.py      MathLib (imported from tools/self-improving-code-analyzer)
        ├── assistant.py    Claude chat behind the gate (concept from OmniGPT / Neural Sovereign)
        ├── inventory.py    static analysis of all of sources/ -> catalog.json
        └── catalog.py      project catalog + where each project's features surface
```

## Flow of a governed request
client -> `api.py` -> `gated()` stamps platform evidence (mission, auditable, provenance) and merges
client attributes (harm, intent...) -> 10 commandments -> audit entry -> allowed? run feature : HTTP 403.
Clients cannot override the three evidence fields.

## How each source project is combined
| Source | Mode | Result |
|---|---|---|
| services/covenant | imported unchanged (path wiring in `sources.py`) | governance gate, 10 rules |
| tools/self-improving-code-analyzer | imported unchanged | `/v1/math/gcd-lcm` |
| research/circuit-lower-bounds | imported if deps present; Bayesian logic re-implemented | `/v1/stats/*` |
| services/autonomous-ai | re-implemented cleanly (originals have syntax errors / pandas+sklearn deps) | `/v1/decide`, `/v1/recommend` |
| services/aeon-engine | re-implemented headless (original is a Tkinter GUI) | `/v1/protocols/*` |
| apps/sites/*, hybrid-sat-solver-portal | served as static mounts | `/sites/<name>` |
| OmniGPT / Neural Sovereign idea | new `assistant.py` | `/v1/assistant` |
| everything else (Vantage, Quantum Flow OS, Site Mirror, Android/Expo apps, Codegenie, UUMA, ...) | cataloged + analyzed, run standalone | `/v1/catalog`, `/v1/inventory` |

## Deliberately not wired
- **UUMA** (mining framework): catalogued only; no mining is started by the platform.
- Heavy standalone apps (Site Mirror, Vantage, Quantum Flow OS): need their own build/runtime; they are listed with their stack and size rather than embedded.
- Known broken sources found by the analyzer: `services/autonomous-ai` (3 files with syntax errors) and `research/circuit-lower-bounds` (1) - see `GET /v1/inventory`.


## Tenant identity rollout boundary

PostgreSQL migration 006 introduces tenant, principal, membership, and API
credential records. `GET /v1/identity/me` authenticates a tenant-specific credential against an explicit
tenant header and reports the assigned role permissions. The dedicated tenant
evidence routes use a separate forced-RLS table, per-tenant idempotency, and
principal-attributed audit events.

Tenant credentials are accepted only by explicitly allowlisted identity and
`/v1/tenant/*` routes. In addition to tenant evidence, audit, administration,
source acquisition, and governance, stateless decision, recommendation, AEON,
statistics, and math operations are exposed through tenant-specific routes. These
operations require `governance:execute`, pass through COVENANT, and write their
decision and request lifecycle events to the selected tenant's audit chain.

The legacy global business routes still use the shared token because their stores
and mutable state have not completed tenant-level isolation. Enabling tenant
credentials across those routes before scoping every read, write, idempotency key,
and audit query would create a cross-tenant data exposure risk.


Tenant evidence uses a separate PostgreSQL table and adapter. It has forced row-level
security, per-tenant idempotency, tenant-local hash chains, and principal-attributed
audit events. The original global evidence ledger remains separate for legacy
single-tenant callers; no historical evidence is silently assigned to a tenant.


## Tenant administration and source acquisition

The tenant identity layer now supports owner/admin membership lifecycle operations,
credential issuance and revocation, and tenant-aware controlled source acquisition.
Membership and credential mutations are serialized and audited in the same
PostgreSQL transaction. PostgreSQL RLS scopes tenant, membership, credential, and
tenant-evidence rows from a transaction-local tenant identifier. Only a tenant
owner may assign the owner role or modify an existing owner's membership; the last
active owner cannot be demoted or suspended.

The tenant source connector applies COVENANT authorization before outbound network
access and appends the signed fetch observation to the selected tenant's separate
evidence ledger. Stateless tenant platform operations use the same COVENANT and
tenant-audit boundary. The global evidence and governance routes remain behind the
legacy shared token until their storage and query paths are tenant-aware.

API credentials are tenant-bound: the credential row carries one tenant UUID, the
authentication query matches that tenant explicitly, and the RLS policy enforces
the same boundary. Suspending a membership revokes its active credentials in the
same transaction, so reactivation never silently restores old bearer tokens.


## Tenant-local audit and governance

Migration 010 creates an append-only audit table with forced row-level security.
Each tenant has an independent event index, predecessor hash, and verification scope;
there is no global sequence exposed through tenant audit queries. Authenticated
tenant request lifecycle events, membership and credential changes, evidence
mutations, and COVENANT decisions are written to the selected tenant's chain.
The tenant audit API exposes only tenant-local listing and full-chain verification.
The global audit ledger remains reserved for legacy/global operations and does not
receive authenticated tenant request events or tenant governance payloads.


## Tenant-specific decision policy

Migration 011 stores tenant-owned decision rules in PostgreSQL with forced RLS,
tenant-scoped uniqueness, constrained operators and fields, and creator/updater
attribution. Owner/admin roles manage rules; other tenant roles may read them.
Rule create/update/delete operations are COVENANT-gated and append their audit
event in the same transaction as the rule mutation. Tenant decisions compose the
tenant's enabled rules with the platform defaults without mutating the shared
legacy decision engine. The legacy global rule API remains isolated behind the
shared token.


## Tenant-isolated assistant conversations

Migration 012 stores assistant conversations and message history in PostgreSQL with
forced RLS and transaction-local tenant/principal scope. Tenant assistant requests
load prior context only from the authenticated tenant's conversation. Client-supplied
history is never trusted. Conversation creation and completed exchanges are
principal-attributed in the tenant audit chain. Assistant access is separately
permissioned through `assistant:use`; the Anthropic provider credential and billing
remain platform-managed rather than tenant-managed. Message history is append-only
through the application runtime role.


## Unified tenant workspace

The FastAPI-served console at `/` exposes the tenant-aware OMNIS capabilities in
one browser workspace. Tenant credentials are entered separately from the legacy
global API token and are used only with the matching `X-OMNIS-Tenant` header.
The browser obtains its role and permissions from `/v1/identity/me`; all feature
requests continue to pass through the tenant authentication middleware and the
underlying per-route permission checks.

The workspace currently surfaces tenant usage summaries, tenant audit listing
and verification, tenant decision-rule management, and tenant assistant
conversations. Conversation history is fetched from the PostgreSQL tenant store
through `GET /v1/tenant/assistant/conversations/{conversation_id}`; no browser
supplied history is trusted by the generation endpoint. The console keeps the
credential in page memory only and does not persist it to local storage.
