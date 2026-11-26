/**
 * Vantage Sentinel — Cloudflare Worker entry point.
 *
 * Read paths are public and expose only verified operational facts. The one
 * write path requires an operator bearer token; the cron trigger runs the same
 * collection cycle without an HTTP request. No credential is ever returned.
 */
import { DASHBOARD_HTML } from "./dashboard.js";
import {
  latestBriefing,
  latestSnapshot,
  recentSnapshots,
  runCycle,
} from "./collect.js";

const HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer",
  "permissions-policy": "camera=(), microphone=(), geolocation=()",
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: HEADERS });
}

function tokenMatches(supplied, expected) {
  if (typeof supplied !== "string" || typeof expected !== "string" || supplied.length !== expected.length) return false;
  let difference = 0;
  for (let index = 0; index < supplied.length; index += 1) {
    difference |= supplied.charCodeAt(index) ^ expected.charCodeAt(index);
  }
  return difference === 0;
}

function html(body) {
  return new Response(body, {
    headers: {
      ...HEADERS,
      "content-type": "text/html; charset=utf-8",
      "content-security-policy":
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
    },
  });
}

async function statusResponse(env) {
  let snapshot = await latestSnapshot(env);
  if (!snapshot) {
    await runCycle(env);
    snapshot = await latestSnapshot(env);
  }
  if (!snapshot) return json({ ok: false, error: "No observation could be recorded." }, 503);
  return json({
    ok: true,
    service: "vantage-sentinel",
    status: snapshot.status,
    capturedAt: snapshot.capturedAt,
    facts: snapshot.facts,
    reasons: snapshot.facts?.reasons ?? [],
  });
}

async function handle(request, env) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";

  if (path === "/" && request.method === "GET") return html(DASHBOARD_HTML);

  if (path === "/api/health" && request.method === "GET") {
    return json({
      ok: true,
      service: "vantage-sentinel",
      time: new Date().toISOString(),
      database: Boolean(env.DB),
      modelConfigured: Boolean(env.OPENAI_API_KEY),
      githubConfigured: Boolean(env.GITHUB_TOKEN),
    });
  }

  if (path === "/api/status" && request.method === "GET") return statusResponse(env);

  if (path === "/api/briefing" && request.method === "GET") {
    const briefing = await latestBriefing(env);
    return json({ ok: Boolean(briefing), briefing });
  }

  if (path === "/api/snapshots" && request.method === "GET") {
    const snapshots = await recentSnapshots(env, url.searchParams.get("limit") || 24);
    return json({ ok: true, snapshots });
  }

  if (path === "/api/refresh" && request.method === "POST") {
    const supplied = request.headers.get("authorization")?.replace(/^Bearer\s+/i, "") ?? "";
    if (!env.SENTINEL_ADMIN_TOKEN || !supplied || !tokenMatches(supplied, env.SENTINEL_ADMIN_TOKEN)) {
      return json({ ok: false, error: "Unauthorized" }, 401);
    }
    const result = await runCycle(env);
    return json({ ok: true, ...result });
  }

  return json({ ok: false, error: "Not found" }, 404);
}

export default {
  async fetch(request, env) {
    try {
      return await handle(request, env);
    } catch (error) {
      console.error("[sentinel] request failed", error?.message ?? "unknown error");
      return json({ ok: false, error: "The control plane could not complete this request." }, 500);
    }
  },
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(
      runCycle(env).catch((error) => {
        console.error("[sentinel] scheduled cycle failed", error?.message ?? "unknown error");
      }),
    );
  },
};
