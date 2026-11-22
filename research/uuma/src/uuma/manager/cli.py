"""CLI. Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>
    python -m uuma.manager.cli init    --vault v.json      (prompts for mnemonic + password)
    python -m uuma.manager.cli dry-run --vault v.json --bits 8 --max-nonce 100000
"""
from __future__ import annotations
import argparse, getpass, sys

from ..core.algorithm import UnifiedUniversalMiningAlgorithm
from ..core.phases import build_default_simulated_phases
from ..wallet import vault
from .backend import DryRunBackend
from .manager import Manager


def _payout(secret: bytes) -> str:
    from ..wallet.hd import HDWallet  # needs bip-utils
    return HDWallet.from_mnemonic(secret.decode()).uuma_experimental().address


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="uuma-manager")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "dry-run"):
        p = sub.add_parser(name); p.add_argument("--vault", required=True)
    d = sub.choices["dry-run"]; d.add_argument("--bits", type=int, default=8)
    d.add_argument("--max-nonce", type=int, default=100_000); d.add_argument("--ledger")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        vault.save(a.vault, getpass.getpass("Mnemonic: ").encode(), getpass.getpass("New password: "))
        print("vault written"); return 0
    alg = UnifiedUniversalMiningAlgorithm(build_default_simulated_phases())
    m = Manager("uuma-dryrun", DryRunBackend(alg, a.bits), alg, a.vault,
                lambda: getpass.getpass("Password: "), _payout, a.ledger)
    s = m.run_once(a.max_nonce)
    print("no share found" if s is None else f"share accepted: nonce={s.nonce} digest={s.digest.hex()}")
    return 0 if s else 1


if __name__ == "__main__":
    sys.exit(main())
