import json
import pytest
from uuma.core.algorithm import UnifiedUniversalMiningAlgorithm
from uuma.core.phases import build_default_simulated_phases
from uuma.manager.backend import DryRunBackend, Share
from uuma.manager.chains import CHAINS, get_chain
from uuma.manager.manager import Manager
from uuma.wallet import vault
from uuma.wallet.vault import VaultError

SECRET = b"test secret words not a real wallet"

def _setup(tmp_path, bits=4):
    alg = UnifiedUniversalMiningAlgorithm(build_default_simulated_phases())
    be = DryRunBackend(alg, bits)
    vp = str(tmp_path / "v.json"); vault.save(vp, SECRET, "pw", vault.MIN_N)
    payout = lambda s: "test-payout-label"  # test stand-in; real path uses HDWallet
    return alg, be, vp, payout

def test_dry_run_finds_and_backend_verifies_share(tmp_path):
    alg, be, vp, payout = _setup(tmp_path)
    m = Manager("uuma-dryrun", be, alg, vp, lambda: "pw", payout, str(tmp_path / "l.jsonl"))
    share = m.run_once(5000)
    assert share is not None and len(be.accepted) == 1
    # independent recomputation
    job_data = __import__("hashlib").sha256(b"uuma-dryrun-job" + (0).to_bytes(8, "big")).digest()
    assert alg.hash_once(job_data, share.nonce) == share.digest

def test_backend_rejects_forged_and_unknown_shares(tmp_path):
    alg, be, vp, payout = _setup(tmp_path)
    job = be.get_job()
    assert not be.submit_share(Share(job.job_id, 0, b"\x00" * 32, "x"))   # forged digest
    assert not be.submit_share(Share(999, 0, b"\x00" * 32, "x"))          # unknown job
    assert not be.submit_share(Share(job.job_id, -1, b"\x00" * 32, "x"))  # bad nonce

def test_wrong_password_fails_before_any_work(tmp_path):
    alg, be, vp, payout = _setup(tmp_path)
    m = Manager("uuma-dryrun", be, alg, vp, lambda: "bad", payout)
    with pytest.raises(VaultError):
        m.run_once(10)
    assert be._next == 0  # no job was even fetched

def test_exhausted_search_returns_none(tmp_path):
    alg, be, vp, payout = _setup(tmp_path, bits=64)
    assert Manager("uuma-dryrun", be, alg, vp, lambda: "pw", payout).run_once(3) is None

def test_real_chains_are_not_implemented(tmp_path):
    alg, be, vp, payout = _setup(tmp_path)
    for k, spec in CHAINS.items():
        if not spec.implemented:
            with pytest.raises(NotImplementedError):
                get_chain(k)
            with pytest.raises(NotImplementedError):
                Manager(k, be, alg, vp, lambda: "pw", payout)
    with pytest.raises(KeyError):
        get_chain("nope")

def test_secret_never_written_to_ledger(tmp_path):
    alg, be, vp, payout = _setup(tmp_path)
    lp = tmp_path / "l.jsonl"
    Manager("uuma-dryrun", be, alg, vp, lambda: "pw", payout, str(lp)).run_once(5000)
    text = lp.read_text()
    assert SECRET.decode() not in text and json.loads(text.splitlines()[0])["accepted"] is True

def test_concurrent_get_job_ids_are_unique(tmp_path):
    import threading
    alg, be, vp, payout = _setup(tmp_path)
    ids, ts = [], [threading.Thread(target=lambda: ids.append(be.get_job().job_id)) for _ in range(50)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sorted(ids) == list(range(50))
