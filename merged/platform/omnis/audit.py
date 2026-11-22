# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Tamper-evident audit trail for API request lifecycle and governed decisions."""
import hashlib
import json
import threading
import time


class AuditLog:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.entries: list[dict] = []

    def record(self, kind: str, payload: dict, actor: str | None = None) -> dict:
        with self._lock:
            prev = self.entries[-1]["hash"] if self.entries else "0" * 64
            body = {"i": len(self.entries), "ts": time.time(), "kind": kind, "payload": payload, "prev": prev}
            if actor is not None:
                if not isinstance(actor, str) or not actor.strip():
                    raise ValueError("audit actor must be a non-empty string")
                body["actor"] = actor.strip()
            body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
            self.entries.append(body)
            return body

    def verify(self) -> bool:
        with self._lock:
            prev = "0" * 64
            for index, entry in enumerate(self.entries):
                body = {key: value for key, value in entry.items() if key != "hash"}
                if (body.get("i") != index or body.get("prev") != prev or
                        hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != entry.get("hash")):
                    return False
                prev = entry["hash"]
            return True

    def snapshot(self, limit: int = 50) -> dict:
        """Verify and return audit entries under one in-memory lock."""
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500")
        with self._lock:
            prev = "0" * 64
            for index, entry in enumerate(self.entries):
                body = {key: value for key, value in entry.items() if key != "hash"}
                expected = hashlib.sha256(
                    json.dumps(body, sort_keys=True, default=str).encode()
                ).hexdigest()
                if body.get("i") != index or body.get("prev") != prev or expected != entry.get("hash"):
                    return {"verification": {"valid": False, "reason": "chain_mismatch",
                                             "failed_index": index}, "entries": []}
                prev = entry["hash"]
            return {
                "verification": {"valid": True, "checked": len(self.entries), "head": prev},
                "entries": [dict(entry) for entry in self.entries[-limit:]],
            }

    def list(self, limit: int = 50) -> list[dict]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500")
        with self._lock:
            return [dict(entry) for entry in self.entries[-limit:]]


audit = AuditLog()
