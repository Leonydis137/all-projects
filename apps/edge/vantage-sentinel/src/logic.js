/**
 * Pure decision logic for Vantage Sentinel.
 *
 * Every input here comes from a real observation: an HTTP health response, a
 * D1 row, or a GitHub API response. This module never invents a value, never
 * falls back to a default "healthy" state, and never reads a secret. Keeping
 * it pure makes the incident rules testable without touching production.
 */

export const FRESHNESS_MS = 60 * 60 * 1000;

/** Parse ISO 8601 and the timestamp shapes Cloudflare/D1 return, as UTC. */
export function parseTimestamp(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const raw = value.trim();
  // SQLite timestamps have no zone marker. Normalise them before Date.parse,
  // which would otherwise read them in the host's local timezone.
  const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(raw)
    ? raw.replace(" ", "T") + "Z"
    : raw;
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function isFresh(value, now = new Date(), maxAgeMs = FRESHNESS_MS) {
  const parsed = parseTimestamp(value);
  if (parsed === null) return false;
  const age = now.getTime() - parsed;
  return age >= -60_000 && age <= maxAgeMs;
}

function condition(ok, error, problemDetail, okDetail) {
  if (error) return { state: "error", detail: error };
  if (!ok) return { state: "degraded", detail: problemDetail };
  return { state: "ok", detail: okDetail };
}

/**
 * Turn observed facts into an honest overall status.
 *
 * An unreachable source is never treated as healthy: it is either `stale`
 * (we have a value but it is old) or `error` (we could not observe it at all).
 * Only `operational` means every critical source was observed recently and
 * reported itself healthy.
 */
export function deriveOverall(facts, now = new Date()) {
  const app = condition(
    facts?.app?.ok === true,
    facts?.app?.error,
    facts?.app?.summary || "The main desk did not report operational.",
    "The main desk reports operational.",
  );
  // The companion Worker is observed through the Cloudflare API. Its own tick
  // freshness is a separate D1 signal so that a slow health route cannot make
  // a deployed edge script look unavailable.
  const worker = condition(
    facts?.worker?.ok === true && facts?.worker?.subdomainEnabled !== false,
    facts?.worker?.error,
    "The companion Worker is not enabled on its public subdomain.",
    `The companion Worker ${facts?.worker?.name ?? "vantage-ars"} is deployed${facts?.worker?.deployedAt ? ` (updated ${facts.worker.deployedAt})` : ""}.`,
  );
  const dbFresh = isFresh(facts?.database?.lastSuccess, now);
  const database = condition(
    facts?.database?.ok === true && !facts?.database?.lastError && dbFresh,
    facts?.database?.error,
    facts?.database?.lastError
      ? `The agent database recorded an error: ${facts.database.lastError}`
      : facts?.database?.lastSuccess
        ? `The agent database's last recorded success was ${facts.database.lastSuccess}.`
        : "The agent database has not recorded a successful tick.",
    `The agent database last succeeded at ${facts.database.lastSuccess}.`,
  );
  const github = condition(
    facts?.github?.ok === true,
    facts?.github?.error,
    "GitHub could not be observed.",
    "GitHub pipeline and repository activity were observed.",
  );

  const sources = { app, worker, database, github };
  const critical = [app, worker, database];
  const reasons = Object.entries(sources)
    .filter(([, value]) => value.state !== "ok")
    .map(([name, value]) => `${name}: ${value.detail}`);

  let status = "operational";
  if (critical.some((source) => source.state === "error")) status = "incident";
  else if (critical.some((source) => source.state !== "ok")) status = "degraded";
  else if (github.state !== "ok") status = "degraded";

  return { status, sources, reasons };
}

export function numericTokens(value) {
  const matches = String(value ?? "").match(/\d+(?:\.\d+)?/g);
  return matches ? [...new Set(matches)] : [];
}

/**
 * A model briefing is usable only if it is well formed and introduces no new
 * numbers. Numbers are the easiest thing to fabricate in an incident summary,
 * so every numeral in the output must also appear in the verified facts.
 */
export function validateBriefing(text, facts) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { ok: false, reason: "The model did not return JSON." };
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, reason: "The model returned an unexpected shape." };
  }
  const headline = typeof parsed.headline === "string" ? parsed.headline.trim() : "";
  const summary = typeof parsed.summary === "string" ? parsed.summary.trim() : "";
  const actions = Array.isArray(parsed.actions) ? parsed.actions.filter((a) => typeof a === "string") : [];
  if (!headline || headline.length > 120) {
    return { ok: false, reason: "The headline was missing or too long." };
  }
  if (!summary || summary.length > 700) {
    return { ok: false, reason: "The summary was missing or too long." };
  }
  if (actions.length > 3 || actions.some((a) => !a.trim() || a.length > 180)) {
    return { ok: false, reason: "The action list was malformed." };
  }
  const allowed = new Set(numericTokens(JSON.stringify(facts)));
  const introduced = numericTokens(`${headline} ${summary} ${actions.join(" ")}`).filter(
    (token) => !allowed.has(token),
  );
  if (introduced.length) {
    return { ok: false, reason: `The model introduced unverified numbers: ${introduced.join(", ")}` };
  }
  return {
    ok: true,
    briefing: { headline, summary, actions: actions.map((a) => a.trim()) },
  };
}

/**
 * Deterministic operator digest built only from fields in the verified fact
 * set. This is used when the language provider is unavailable; it is labelled
 * `deterministic` and is never presented as an AI-generated briefing.
 */
export function buildFactDigest(facts) {
  const overall = String(facts?.overall ?? "unknown");
  const failedChecks = (Array.isArray(facts?.app?.checks) ? facts.app.checks : [])
    .filter((check) => check?.ok !== true)
    .map((check) => `${check.label}: ${check.detail}`.trim().replace(/[.;,]+$/, ""));
  const summaryParts = [];
  if (facts?.app?.summary) summaryParts.push(`Main desk: ${facts.app.summary}`);
  else if (facts?.app?.state) summaryParts.push(`Main desk state: ${facts.app.state}.`);
  if (failedChecks.length) summaryParts.push(`Failed checks: ${failedChecks.join("; ")}.`);
  const worker = facts?.worker ?? {};
  if (worker.ok) {
    summaryParts.push(
      `Companion Worker ${worker.name ?? "vantage-ars"} is deployed${worker.deployedAt ? ` (updated ${worker.deployedAt})` : ""}.`,
    );
  }
  const db = facts?.database ?? {};
  if (db.ok && db.lastSuccess) summaryParts.push(`Agent database last succeeded at ${db.lastSuccess}.`);
  if (Number(db.pendingDecisions) > 0) summaryParts.push(`${db.pendingDecisions} decisions are pending.`);
  if (facts?.github?.ok && facts.github.repo) summaryParts.push(`Repository ${facts.github.repo} was observed.`);

  const actions = failedChecks.map((check) => `Review ${check}`);
  if (Number(db.pendingDecisions) > 0) actions.push(`Review ${db.pendingDecisions} pending decisions.`);
  if (!actions.length && facts?.app?.ok !== true) actions.push("Inspect the main desk health response.");

  return {
    headline: `Vantage desk: ${overall}`.slice(0, 120),
    summary: summaryParts.join(" ").slice(0, 700) || "No descriptive facts were available in this observation.",
    actions: [...new Set(actions)].slice(0, 3),
  };
}

/** Never echo a credential, even if a source accidentally includes one. */
export function redact(text) {
  return String(text ?? "").replace(
    /(ghp_|github_pat_|sk-[A-Za-z0-9_-]{8,}|cfat_|oc_sk_)[A-Za-z0-9_.-]+/g,
    "[redacted]",
  );
}
