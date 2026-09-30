"""Stratum V1 protocol layer (newline-delimited JSON-RPC 2.0-ish over TCP).

Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>
Protocol framing and client state only. It is NOT wired to any real pool or
chain, and speaking Stratum does not make UUMA compatible with any coin's PoW.
"""
from __future__ import annotations
import json, socket, ssl
from typing import Any, Optional

MAX_LINE = 65536


class StratumError(Exception):
    """Malformed message, oversized line, connection loss, or server error reply."""


def encode(msg: dict) -> bytes:
    return json.dumps(msg, separators=(",", ":")).encode() + b"\n"


def decode(line: bytes) -> dict:
    if len(line) > MAX_LINE:
        raise StratumError("line too long")
    try:
        msg = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise StratumError("malformed JSON") from None
    if not isinstance(msg, dict):
        raise StratumError("message must be an object")
    return msg


class StratumClient:
    def __init__(self, host: str, port: int, timeout: float = 5.0,
                 tls: bool = False, cafile: Optional[str] = None) -> None:
        """tls=True verifies the server certificate and hostname (system CAs, or cafile if given)."""
        try:
            self._sock = socket.create_connection((host, port), timeout=timeout)
            if tls:
                self._sock = ssl.create_default_context(cafile=cafile).wrap_socket(self._sock, server_hostname=host)
        except (ssl.SSLError, OSError) as e:
            raise StratumError(f"connection failed: {e.__class__.__name__}") from None
        self._f = self._sock.makefile("rb")
        self._id = 0
        self.difficulty: Optional[float] = None
        self.current_job: Optional[list] = None
        self.extranonce1: Optional[str] = None
        self.extranonce2_size: Optional[int] = None

    def close(self) -> None:
        self._f.close(); self._sock.close()

    def _read(self) -> dict:
        line = self._f.readline(MAX_LINE + 1)
        if not line:
            raise StratumError("connection closed")
        if not line.endswith(b"\n"):
            raise StratumError("line too long")
        return decode(line)

    def _notify(self, msg: dict) -> None:
        params = msg.get("params")
        if not isinstance(params, list):
            raise StratumError("notification params must be a list")
        if msg["method"] == "mining.set_difficulty" and params and isinstance(params[0], (int, float)):
            self.difficulty = float(params[0])
        elif msg["method"] == "mining.notify":
            self.current_job = params

    def call(self, method: str, params: list) -> Any:
        self._id += 1
        rid = self._id
        self._sock.sendall(encode({"id": rid, "method": method, "params": params}))
        while True:
            msg = self._read()
            if msg.get("method"):          # server notification, may arrive before our reply
                self._notify(msg)
                continue
            if msg.get("id") != rid:
                raise StratumError("unexpected response id")
            if msg.get("error"):
                raise StratumError(f"server error: {msg['error']}")
            return msg.get("result")

    def subscribe(self, agent: str = "uuma-manager/0") -> None:
        res = self.call("mining.subscribe", [agent])
        if not (isinstance(res, list) and len(res) == 3):
            raise StratumError("bad subscribe result")
        _, self.extranonce1, self.extranonce2_size = res

    def authorize(self, worker: str, password: str = "") -> bool:
        return bool(self.call("mining.authorize", [worker, password]))

    def submit(self, worker: str, job_id: str, extranonce2: str, ntime: str, nonce: str) -> bool:
        return bool(self.call("mining.submit", [worker, job_id, extranonce2, ntime, nonce]))
