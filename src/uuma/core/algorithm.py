from __future__ import annotations
import time
from typing import Iterable, Optional

from .difficulty import meets_difficulty
from .types import PhasePlugin, PhaseResult


class UnifiedUniversalMiningAlgorithm:
    """Deterministic sequential pipeline over pluggable phases.

    This is a research construction. It does not implement, claim
    compatibility with, or substitute for any existing blockchain's
    consensus rules.
    """

    def __init__(self, phases: Iterable[PhasePlugin]) -> None:
        phases = list(phases)
        if not phases:
            raise ValueError("At least one phase is required")
        self.phases = phases

    def hash_once(self, data: bytes, nonce: int) -> bytes:
        state = data
        for phase in self.phases:
            state = phase.execute(state, nonce)
        return state

    def search(
        self,
        data: bytes,
        target_bits: int,
        start_nonce: int = 0,
        max_nonce: Optional[int] = None,
    ) -> Optional[PhaseResult]:
        t0 = time.perf_counter()
        nonce = start_nonce
        phase_names = tuple(
            getattr(p, "name", type(p).__name__) for p in self.phases
        )
        while max_nonce is None or nonce < max_nonce:
            digest = self.hash_once(data, nonce)
            if meets_difficulty(digest, target_bits):
                return PhaseResult(
                    digest=digest,
                    nonce=nonce,
                    phase_names=phase_names,
                    elapsed_seconds=time.perf_counter() - t0,
                )
            nonce += 1
        return None
