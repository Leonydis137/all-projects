"""Backends. Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>"""
from __future__ import annotations
import hashlib, threading
from dataclasses import dataclass
from typing import Protocol

from ..core.algorithm import UnifiedUniversalMiningAlgorithm
from ..core.difficulty import meets_difficulty


@dataclass(frozen=True)
class Job:
    job_id: int
    data: bytes
    target_bits: int


@dataclass(frozen=True)
class Share:
    job_id: int
    nonce: int
    digest: bytes
    payout: str


class Backend(Protocol):
    def get_job(self) -> Job: ...
    def submit_share(self, share: Share) -> bool: ...


class DryRunBackend:
    """Local, deterministic job source and independent share verifier.

    The verifier recomputes the digest from (job data, nonce) itself and never
    trusts the digest the miner claims.
    """

    def __init__(self, algorithm: UnifiedUniversalMiningAlgorithm, target_bits: int = 8) -> None:
        if target_bits < 0:
            raise ValueError("target_bits must be non-negative")
        self.algorithm, self.target_bits, self._next = algorithm, target_bits, 0
        self._jobs: dict[int, Job] = {}
        self.accepted: list[Share] = []
        self._lock = threading.Lock()

    def get_job(self) -> Job:
        with self._lock:
            jid, self._next = self._next, self._next + 1
            job = Job(jid, hashlib.sha256(b"uuma-dryrun-job" + jid.to_bytes(8, "big")).digest(), self.target_bits)
            self._jobs[jid] = job
        return job

    def submit_share(self, share: Share) -> bool:
        job = self._jobs.get(share.job_id)
        if job is None or share.nonce < 0:
            return False
        digest = self.algorithm.hash_once(job.data, share.nonce)
        ok = digest == share.digest and meets_difficulty(digest, job.target_bits)
        if ok:
            with self._lock:
                self.accepted.append(share)
        return ok
