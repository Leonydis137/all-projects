# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Governed assistant: Claude chat behind the COVENANT gate (concept from OmniGPT / Neural Sovereign)."""
import httpx

from . import config

SYSTEM = ("You are the OMNIS assistant. OMNIS combines governance (COVENANT), decision rules, adaptive protocols, "
          "statistics, a recommender and a project catalog. Be concise, honest, and refuse harmful requests.")


class AssistantUnavailable(RuntimeError):
    pass


async def chat(message: str, history: list[dict] | None = None, max_tokens: int = 800) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise AssistantUnavailable("ANTHROPIC_API_KEY is not set")
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= 12000:\n        raise ValueError("message must contain 1-12000 characters")\n    prior = history or []\n    if len(prior) > 20 or any(not isinstance(item, dict) or item.get("role") not in ("user", "assistant") or not isinstance(item.get("content"), str) for item in prior):\n        raise ValueError("history must contain at most 20 user/assistant messages")\n    msgs = [*prior, {"role": "user", "content": message.strip()}]
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://api.anthropic.com/v1/messages",
                         headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
                         json={"model": config.ANTHROPIC_MODEL, "max_tokens": max_tokens, "system": SYSTEM, "messages": msgs})
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", []))
