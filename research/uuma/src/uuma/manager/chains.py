"""Chain registry. Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>

Only the local research chain is implemented. Real chains are listed so the
limit is explicit in code: asking for one raises NotImplementedError.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ChainSpec:
    key: str
    name: str
    implemented: bool
    note: str


CHAINS = {
    "uuma-dryrun": ChainSpec("uuma-dryrun", "UUMA local dry run", True,
                             "Local research chain. No network, no coins, no value."),
    **{k: ChainSpec(k, n, False, "Not a UUMA target: needs its own PoW, block format and pool protocol.")
       for k, n in (("bitcoin", "Bitcoin"), ("litecoin", "Litecoin"), ("monero", "Monero"),
                    ("ethereum-classic", "Ethereum Classic"), ("zcash", "Zcash"))},
}


def get_chain(key: str) -> ChainSpec:
    if key not in CHAINS:
        raise KeyError(f"unknown chain: {key}")
    spec = CHAINS[key]
    if not spec.implemented:
        raise NotImplementedError(f"{spec.name} backend is not implemented. {spec.note}")
    return spec
