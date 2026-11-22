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
    msgs = [*(history or []), {"role": "user", "content": message}]
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://api.anthropic.com/v1/messages",
                         headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
                         json={"model": config.ANTHROPIC_MODEL, "max_tokens": max_tokens, "system": SYSTEM, "messages": msgs})
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", []))
