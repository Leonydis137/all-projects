# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Tamper-evident audit trail (hash chain) for every governed call."""
import hashlib
import json
import threading
import time


class AuditLog:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.entries: list[dict] = []

    def record(self, kind: str, payload: dict) -> dict:
        with self._lock:
            prev = self.entries[-1]["hash"] if self.entries else "0" * 64
            body = {"i": len(self.entries), "ts": time.time(), "kind": kind, "payload": payload, "prev": prev}
            body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
            self.entries.append(body)
            return body

    def verify(self) -> bool:
        prev = "0" * 64
        for e in self.entries:
            b = {k: v for k, v in e.items() if k != "hash"}
            if b["prev"] != prev or hashlib.sha256(json.dumps(b, sort_keys=True, default=str).encode()).hexdigest() != e["hash"]:
                return False
            prev = e["hash"]
        return True


audit = AuditLog()
