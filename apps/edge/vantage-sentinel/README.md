# Vantage Sentinel

An evidence-first edge control plane for the live Vantage-ARS office. It runs as
a Cloudflare Worker bound to the existing `vantage-data` D1 database, observes
real systems every 15 minutes, records durable snapshots, and asks OpenAI to
phrase a briefing **only from the observations it just verified**.

**No sample data, no simulation, no fallback "healthy" state.** If a source is
unreachable the snapshot says so; if the model refuses or invents a number the
briefing is marked unavailable. The console shows the source facts alongside
the interpretation.

## Live surfaces

| Surface | Purpose |
| --- | --- |
| `GET /` | Self-contained operator console (no external assets) |
| `GET /api/status` | Latest verified snapshot with full source facts |
| `GET /api/briefing` | Latest grounded briefing and its provenance |
| `GET /api/snapshots?limit=24` | Recent observation timeline |
| `GET /api/health` | Worker self-check (configuration presence only) |
| `POST /api/refresh` | Operator-triggered cycle, bearer token required |

## Real sources

1. `APP_HEALTH_URL` — the deployed main desk's `/api/health` response.
2. Companion Worker deployment — Cloudflare's live control-plane record for
   `WORKER_SCRIPT_NAME`, including its public-subdomain state and last update.
3. `DB` — the bound `vantage-data` D1 database: `system_health`, `decision_queue`,
   `agent_tasks`, `activity_log`, `agent_state`, `leads`.
4. GitHub REST API — workflow runs, latest commit and repository metadata for
   `GITHUB_REPO`, authenticated with a scoped token.

Status is derived by `src/logic.js`: a critical source that was not observed, or
that reports a problem, produces `degraded` or `incident`. There is no path that
turns a missing observation into success.

## Briefing guard

The model receives only the collected fact JSON, is told not to add anything,
and must return `{ headline, summary, actions }`. Before storage the output is
reparsed and every numeral in it must already appear in the facts. A new number,
a malformed shape, an API error or a missing key is not silently replaced;
Sentinel emits a `deterministic` digest built solely from the same verified
facts and records the provider error code as provenance. The console labels it
as deterministic, so it is never mistaken for an AI briefing.

## Deploy

```sh
npm test
npx wrangler d1 execute vantage-data --config wrangler.toml --remote --file=schema.sql
npx wrangler secret put OPENAI_API_KEY --config wrangler.toml
npx wrangler secret put GITHUB_TOKEN --config wrangler.toml
npx wrangler secret put SENTINEL_ADMIN_TOKEN --config wrangler.toml
npx wrangler deploy --config wrangler.toml
```

`SENTINEL_ADMIN_TOKEN` is generated with `openssl rand -hex 24` and is only
needed for `/api/refresh`. Secrets are never committed or returned by an API.

`.github/workflows/deploy-sentinel.yml` performs the schema apply and deploy on
changes to this directory; it needs `CLOUDFLARE_API_TOKEN` as a repository
secret.
