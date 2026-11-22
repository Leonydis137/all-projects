# UUMA audit notes and decision log

Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>
Scope: the code added after the uploaded M1 source (native helper, vault, manager). Self-review only; **no external cryptographic review.**

## Decisions
| Decision | Reason |
|---|---|
| Native C helper ports only the buffer-fill loop | Profiling in the project's own note: scrypt is already C; the loop was the remaining Python cost |
| Native path optional, pure Python is the fallback and the reference | Parity is testable; the project still runs without a compiler |
| Vault: scrypt + AES-256-GCM via `cryptography` | Standard, maintained primitives; no home-made crypto. Added as a dependency |
| Vault header bound as AAD; KDF `n` floored and capped | Stops downgrade edits and crafted-file DoS |
| Manager only implements a local dry-run chain | No real chain can be tested here; real ones raise `NotImplementedError` |
| Backend re-computes every share | A miner's claimed digest is never trusted |

## Findings
1. **Fixed:** the manager ledger was created with default permissions, then chmod-ed (a short window). It is now created with mode 0600 directly.
2. **Open:** `del secret` in the manager does not wipe memory. Python `bytes` are immutable and may be copied. The secret can linger in process memory until garbage-collected.
3. **Open:** the payout address is written to the ledger in clear text. It is not a secret, but it links runs to a wallet.
4. **Fixed:** `DryRunBackend` job counter and share list are now lock-protected (test added).
5. **Open:** the password comes from a prompt only, with no lockout or rate limit on repeated wrong guesses (scrypt cost is the only brake).
6. **Partly fixed:** `vault.rekey` changes the password atomically. Still one secret per file, and rekey only changes the password, not the salt-derived key policy beyond a fresh salt.

7. **By design:** `stratum.py` is framing and client state only; it caps line length (64 KiB), rejects non-object JSON, and treats server errors and mismatched reply ids as failures. Optional TLS (`tls=True`) verifies the certificate and hostname; tested with a locally generated self-signed cert (trusted and untrusted cases). It has no reconnect, no pool-specific handling and no certificate pinning. Not reviewed against any real pool; do not use with real funds or a real pool without review.

## Verification status (be precise)
- Native parity: 26 cases run with a plain script; identical to pure Python.
- Vault (11), manager (7) and stratum (7) tests: run with a minimal stand-in for pytest because pytest was not installable in the build environment. Please re-run with real `pytest`.
- The original 54-test suite was not re-run against these changes.
- `uuma.manager.cli` was not executed (needs `bip-utils`, not installed there).
- Benchmarks: 1 CPU, one machine, Python 3.12.3. Not comparable across hardware.

## Still not implemented
Stratum V2, pool integration, all real chain backends, M4–M9 as listed in the README. Not a miner for any existing chain.
