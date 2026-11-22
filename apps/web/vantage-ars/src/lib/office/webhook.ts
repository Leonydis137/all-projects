/**
 * An optional second delivery path for founder notices.
 *
 * SMTP depends on a mailbox and an app password. A founder who wants a push on
 * a phone can set FOUNDER_WEBHOOK_URL instead; the same notice is posted as a
 * short JSON message. The URL is deployment configuration, never customer
 * input, and only HTTPS endpoints without embedded credentials are accepted.
 */
import { env } from "../env";
import type { FounderNotice } from "./notice";

const MAX_BODY = 1800;

export function parseFounderWebhookUrl(raw: string | undefined): URL | null {
  if (!raw) return null;
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return null;
  }
  if (url.protocol !== "https:") return null;
  if (url.username || url.password) return null;
  return url;
}

export function founderWebhookPayload(notice: FounderNotice): string {
  const body = notice.body.length > MAX_BODY ? `${notice.body.slice(0, MAX_BODY)}…` : notice.body;
  // `text` is read by Slack and many generic receivers; `content` is read by
  // Discord. Both are included so one URL works with the common endpoints.
  return JSON.stringify({
    text: `${notice.subject}\n\n${body}`,
    content: `${notice.subject}\n\n${body}`,
    subject: notice.subject,
    kind: notice.kind,
    source: "vantage-ars",
  });
}

const FOUNDER_WEBHOOK_MAX_ATTEMPTS = 3;
const FOUNDER_WEBHOOK_BASE_DELAY_MS = 2_000;
const FOUNDER_WEBHOOK_MAX_DELAY_MS = 30_000;

type FetchLike = (input: string, init: RequestInit) => Promise<Response>;

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });
}

function nextBackoffDelayMs(attempt: number) {
  const delay = Math.min(FOUNDER_WEBHOOK_BASE_DELAY_MS * 2 ** (attempt - 1), FOUNDER_WEBHOOK_MAX_DELAY_MS);
  const jitter = Math.floor(Math.random() * delay);
  return delay + jitter;
}

async function deliverFounderWebhook(
  notice: FounderNotice,
  url: URL | null,
  fetchImpl: FetchLike,
): Promise<{ ok: boolean; detail: string }> {
  if (!url) return { ok: false, detail: "No valid HTTPS founder webhook is configured." };
  try {
    const response = await fetchImpl(url.toString(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: founderWebhookPayload(notice),
      redirect: "error",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) {
      return {
        ok: false,
        detail: `The founder webhook answered ${response.status}.`,
      };
    }
    return { ok: true, detail: "Posted to the founder webhook." };
  } catch {
    return { ok: false, detail: "The founder webhook could not be reached." };
  }
}

export async function postFounderWebhook(
  notice: FounderNotice,
  rawUrl: string | undefined = env("FOUNDER_WEBHOOK_URL"),
  fetchImpl: FetchLike = fetch,
): Promise<{ ok: boolean; detail: string }> {
  const url = parseFounderWebhookUrl(rawUrl);
  if (!url) return { ok: false, detail: "No valid HTTPS founder webhook is configured." };
  let result = await deliverFounderWebhook(notice, url, fetchImpl);
  for (let attempt = 1; attempt < FOUNDER_WEBHOOK_MAX_ATTEMPTS; attempt += 1) {
    if (result.ok) return result;
    await sleep(nextBackoffDelayMs(attempt));
    result = await deliverFounderWebhook(notice, url, fetchImpl);
  }
  return result;
}
