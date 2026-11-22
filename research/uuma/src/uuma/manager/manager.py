"""Manager: unlock vault -> derive payout -> fetch job -> search -> submit.

Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>
The secret is held only inside run_once() and is never logged or returned.
"""
from __future__ import annotations
import json, os
from typing import Callable, Optional

from ..core.algorithm import UnifiedUniversalMiningAlgorithm
from ..wallet import vault
from .backend import Backend, Share
from .chains import get_chain


class Manager:
    def __init__(self, chain: str, backend: Backend, algorithm: UnifiedUniversalMiningAlgorithm,
                 vault_path: str, password_fn: Callable[[], str],
                 payout_fn: Callable[[bytes], str], ledger_path: Optional[str] = None) -> None:
        self.chain = get_chain(chain)  # raises NotImplementedError for real chains
        self.backend, self.algorithm = backend, algorithm
        self.vault_path, self.password_fn, self.payout_fn, self.ledger_path = vault_path, password_fn, payout_fn, ledger_path

    def run_once(self, max_nonce: int) -> Optional[Share]:
        secret = vault.load(self.vault_path, self.password_fn())
        try:
            payout = self.payout_fn(secret)
        finally:
            del secret
        job = self.backend.get_job()
        res = self.algorithm.search(job.data, job.target_bits, 0, max_nonce)
        if res is None:
            self._log({"job": job.job_id, "found": False, "tried": max_nonce})
            return None
        share = Share(job.job_id, res.nonce, res.digest, payout)
        accepted = self.backend.submit_share(share)
        self._log({"job": job.job_id, "found": True, "nonce": res.nonce, "digest": res.digest.hex(),
                   "payout": payout, "accepted": accepted, "elapsed_s": res.elapsed_seconds})
        return share if accepted else None

    def _log(self, rec: dict) -> None:
        if self.ledger_path:
            fd = os.open(self.ledger_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)  # 0600 from creation
            with os.fdopen(fd, "a") as f:
                f.write(json.dumps(rec) + "\n")
