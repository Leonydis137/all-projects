# UUMA — Compositional Proof-of-Work Research Framework

Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>

UUMA is an experimental research framework for compositional
proof-of-work algorithms. It is **not** a universal miner for
existing cryptocurrencies.

## What this project is

Two things, deliberately separated:

1. **A universal mining *manager*** — one application that
   orchestrates HD wallets, per-chain backends, and per-chain
   pool protocols. This is the legitimate engineering product.

2. **A PoW research construction** — the UUMA phase pipeline
   itself, studied for whether sequential composition of
   heterogeneous phases produces measurable hardware-diversity
   advantages over a single-primitive PoW.

## What this project is not

- Not a miner for Bitcoin, Litecoin, Monero, Ethereum Classic,
  Zcash, or any existing chain.
- Not a consensus bypass. Existing chains require their own
  PoW functions, block formats, and difficulty rules.
- Not a quantum-resistant construction. Classical hash
  composition does not grant post-quantum security.
- Not a 51%-attack mitigation. Composition raises cost; it does
  not change the fundamental consensus assumption.
- Not production-ready. No external cryptographic review.

## Current status

| Component | Status |
|---|---|
| Phase pipeline | Implemented, all phases nonce-dependent (fixed — see below) |
| Difficulty evaluator | Implemented, 7/7 test vectors green |
| BIP39/BIP32 derivation | Implemented, seed vector matches Trezor test vectors |
| BIP44 BTC P2PKH encoder | Implemented, matches published vector + genesis-block provenance test |
| BIP84 BTC P2WPKH encoder | Implemented, matches BIP-84 spec test vector |
| BIP44 ETH encoder | Implemented, matches published vector, EIP-55 checksum verified |
| Encrypted vault | Implemented (scrypt + AES-256-GCM, `rekey`); 11 tests; not externally reviewed |
| Stratum V1 | Protocol layer + client only, tested against a local test server; optional verified TLS; not connected to any pool. V2 not started |
| Chain backends | Only the local `uuma-dryrun` chain. Every real chain raises `NotImplementedError` |
| Native hot path | Implemented for the memory-hard buffer fill (optional C extension, parity-tested, ~1.6x on that phase) |

**M0 gate status: GREEN.** `pytest -v` executed in a real virtual
environment: **48 passed, 0 failed** (see `pytest_output.txt`).

**M1 gate status: GREEN.** Reproducible per-phase benchmark run;
see `bench/m1_benchmark.json` and the summary below.

## Bugs found and fixed during the M0 run

The original draft of this codebase was never executed. Running
the real test suite surfaced two classes of defect that code
inspection had missed:

1. **Four of five phases ignored `nonce` entirely.** Only the
   `computational` and `asic_resistance_simulated` phases folded
   the nonce into their state. The other three (`memory_hard`,
   `cpu_friendly`, `mixing`) hashed only `data`, so
   `execute(data, 0) == execute(data, 1)` — a nonce search over
   those phases alone could never move the digest. Fixed by
   seeding every phase's working state with
   `sha256(data + nonce)` before phase-specific logic runs.

2. **`ASICResistancePhaseSimulated._math` crashed on any input
   shorter than 32 bytes** (`IndexError`, since it read
   `data[:32]` but indexed up to 31 regardless of how many bytes
   that slice actually contained). This is exactly the case the
   test suite itself exercises (`phase.execute(b"data", 0)`).
   Fixed by the same nonce-seeding change in (1), which also
   guarantees every phase always receives a 32-byte working
   state.

3. **The BIP84 P2WPKH test fixture had a wrong expected address**
   (`...80jy3j5syk2ku` — a transposed-character typo that was
   never independently re-derived). The actual BIP-84
   specification test vector for this exact mnemonic is
   `bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu`. Verified against
   the BIP-84 mediawiki text itself, not just the code under
   test, before changing the fixture — per this project's own
   rule against editing expected values to force a pass.

## M1 benchmark summary

Single run, 200 iterations per phase, on this container
(`Linux x86_64`, 1 vCPU, Python 3.12.3 — full reproducibility
block in `bench/m1_benchmark.json`):

| Phase | Mean | Ops/sec |
|---|---|---|
| computational | 1.6 µs | ~612,760 |
| memory_hard_simulated | 1.51 ms | ~662 |
| cpu_friendly_simulated | 12.3 µs | ~81,485 |
| mixing_simulated | 114.9 µs | ~8,702 |
| asic_resistance_simulated | 25.5 µs | ~39,276 |
| **full pipeline (5 phases)** | **1.66 ms** | **~604** |

**Finding:** `memory_hard_simulated` (the scrypt-based phase)
accounts for ~86% of total pipeline latency and is the single
dominant cost. Any M2 native-port work should target that phase
first — porting the other four would save comparatively little.

## Design principles

1. Never claim compatibility without implementing the relevant
   specification.
2. Never call a simulated algorithm by the name of the real
   consensus algorithm.
3. Keep cryptographic primitives separate from protocol code.
4. Keep private-key material separate from ordinary application
   state.
5. Measure performance before optimizing it.
6. No component is promoted from "prototype" to "implemented"
   without a deterministic test vector or an interoperability
   test.
7. No test result is inferred from code inspection.

## Install (development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run tests

```bash
pytest -v
```

## Run the benchmark

```bash
python bench/run_benchmark.py
```

## Dependencies

Validated pins (real environment, matches candidates exactly):

- `bip-utils==2.9.3`
- `ecdsa==0.19.0`
- `pycryptodome==3.20.0`

Validated: 2026-09-20, commit `090e52db52afc8e3c2c8e207fa12341d14010f7b`,
Python 3.12.3, `pytest -v` → 48 passed.

## License

See LICENSE.

## Verification note
The M0 gate (48 tests) and the reported 54-test run come from `pytest_output.txt`. Vault, manager, stratum and native-parity tests added afterwards were executed with a minimal stand-in for pytest in an environment where pytest could not be installed. Re-run `pip install -e .[dev] && pytest` before relying on any of them. Without pytest, `python tools/run_tests.py` runs the original difficulty and phase tests plus the 51 added tests (89 in total with the native helper built) with plain Python; wallet tests are skipped unless bip-utils is installed (build the native helper first with `python setup.py build_ext --inplace`, or its 26 parity cases are skipped). See `docs/AUDIT.md`.

## Continuous testing
`.github/workflows/tests.yml` runs the full `pytest` suite (including the wallet tests) on GitHub Actions for Python 3.10 and 3.12 and saves `pytest_output.txt` as a downloadable artifact. It has not been run yet: it was written without access to GitHub.
