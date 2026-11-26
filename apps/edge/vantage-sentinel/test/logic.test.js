import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  buildFactDigest,
  deriveOverall,
  isFresh,
  numericTokens,
  parseTimestamp,
  redact,
  validateBriefing,
} from "../src/logic.js";

const NOW = new Date("2026-11-26T12:00:00.000Z");

function facts(overrides = {}) {
  return {
    capturedAt: NOW.toISOString(),
    app: { ok: true, state: "operational", summary: "Operational", error: null },
    worker: {
      ok: true,
      name: "vantage-ars",
      deployedAt: "2026-11-26 11:45:00",
      subdomainEnabled: true,
      error: null,
    },
    database: {
      ok: true,
      lastSuccess: "2026-11-26 11:45:00",
      lastError: "",
      error: null,
    },
    github: { ok: true, error: null },
    ...overrides,
  };
}

describe("observation freshness", () => {
  it("parses ISO and SQLite timestamps as UTC", () => {
    assert.equal(parseTimestamp("2026-11-26T11:45:00Z"), Date.parse("2026-11-26T11:45:00Z"));
    assert.equal(parseTimestamp("2026-11-26 11:45:00"), Date.parse("2026-11-26T11:45:00Z"));
    assert.equal(parseTimestamp("not a date"), null);
  });
  it("rejects old and future observations", () => {
    assert.equal(isFresh("2026-11-26 11:45:00", NOW), true);
    assert.equal(isFresh("2026-11-26 09:00:00", NOW), false);
    assert.equal(isFresh("2026-11-26 13:00:00", NOW), false);
    assert.equal(isFresh("", NOW), false);
  });
});

describe("incident rules", () => {
  it("reports operational only from fresh, healthy observations", () => {
    const result = deriveOverall(facts(), NOW);
    assert.equal(result.status, "operational");
    assert.deepEqual(result.reasons, []);
  });
  it("reports degraded when the main desk reports degraded", () => {
    const result = deriveOverall(
      facts({ app: { ok: false, state: "degraded", summary: "Scheduled work is behind.", error: null } }),
      NOW,
    );
    assert.equal(result.status, "degraded");
    assert.match(result.reasons.join(" "), /Scheduled work is behind/);
  });
  it("reports an incident when a critical source cannot be observed", () => {
    const result = deriveOverall(facts({ database: { ok: false, error: "D1 unavailable" } }), NOW);
    assert.equal(result.status, "incident");
  });
  it("does not call a disabled edge deployment healthy", () => {
    const result = deriveOverall(
      facts({ worker: { ok: true, name: "vantage-ars", subdomainEnabled: false, error: null } }),
      NOW,
    );
    assert.equal(result.status, "degraded");
    assert.equal(result.sources.worker.state, "degraded");
  });
  it("treats GitHub as advisory rather than critical", () => {
    const result = deriveOverall(facts({ github: { ok: false, error: "GitHub timeout" } }), NOW);
    assert.equal(result.status, "degraded");
    assert.equal(result.sources.github.state, "error");
  });
});

describe("grounded briefing validation", () => {
  const observed = { app: { state: "operational" }, worker: { pendingApprovals: 8 } };
  it("accepts a briefing that uses only observed numbers", () => {
    const result = validateBriefing(
      JSON.stringify({
        headline: "Desk operational with 8 approvals waiting",
        summary: "All critical sources were observed. 8 approvals are waiting.",
        actions: ["Review approvals"],
      }),
      observed,
    );
    assert.equal(result.ok, true);
    assert.equal(result.briefing.actions.length, 1);
  });
  it("rejects invented numbers", () => {
    const result = validateBriefing(
      JSON.stringify({ headline: "99 incidents resolved", summary: "Revenue up 40%", actions: [] }),
      observed,
    );
    assert.equal(result.ok, false);
    assert.match(result.reason, /unverified numbers/);
  });
  it("rejects malformed output", () => {
    assert.equal(validateBriefing("not json", observed).ok, false);
    assert.equal(validateBriefing(JSON.stringify({ headline: "", summary: "x" }), observed).ok, false);
    assert.equal(
      validateBriefing(JSON.stringify({ headline: "ok", summary: "ok", actions: ["a", "b", "c", "d"] }), observed).ok,
      false,
    );
  });
  it("extracts unique numeric tokens", () => {
    assert.deepEqual(numericTokens("8 approvals, 8 seen, 1.5 hours"), ["8", "1.5"]);
  });
});

describe("deterministic digest", () => {
  it("uses only verified facts and passes the same guard as model output", () => {
    const digest = buildFactDigest({ ...facts(), overall: "operational" });
    assert.equal(digest.headline, "Vantage desk: operational");
    assert.match(digest.summary, /Main desk: Operational/);
    assert.deepEqual(digest.actions, []);
    assert.equal(validateBriefing(JSON.stringify(digest), { ...facts(), overall: "operational" }).ok, true);
  });
  it("turns failed checks into operator actions without inventing details", () => {
    const observed = facts({
      app: {
        ok: false,
        state: "degraded",
        summary: "The desk is reachable, but a check needs attention.",
        checks: [{ id: "scheduled-desk", label: "Scheduled desk", ok: false, detail: "Scheduled work is behind." }],
      },
      database: { ok: true, lastSuccess: "2026-11-26 11:45:00", lastError: "", pendingDecisions: 8 },
    });
    const digest = buildFactDigest({ ...observed, overall: "degraded" });
    assert.equal(digest.actions.length, 2);
    assert.match(digest.actions.join(" "), /Scheduled work is behind/);
    assert.match(digest.actions.join(" "), /8 pending decisions/);
    assert.equal(validateBriefing(JSON.stringify(digest), { ...observed, overall: "degraded" }).ok, true);
  });
});

describe("secret redaction", () => {
  it("removes token-looking values", () => {
    assert.equal(redact("Bearer sk-abcdefgh12345678 failed"), "Bearer [redacted] failed");
    assert.equal(redact("github_pat_abcdef123456"), "[redacted]");
  });
});
