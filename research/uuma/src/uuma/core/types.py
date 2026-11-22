from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class PhasePlugin(Protocol):
    """A deterministic transform from (bytes, nonce) to bytes.

    Implementations MUST:
    - accept bytes and return bytes
    - be deterministic for identical inputs
    - not hold mutable state that affects output
    """
    name: str

    def execute(self, data: bytes, nonce: int) -> bytes: ...


@dataclass(frozen=True)
class PhaseResult:
    digest: bytes
    nonce: int
    phase_names: tuple[str, ...]
    elapsed_seconds: float
