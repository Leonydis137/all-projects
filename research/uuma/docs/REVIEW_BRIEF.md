# UUMA: brief for an external security reviewer

Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>
Status: research prototype. Self-reviewed only (see `docs/AUDIT.md`). **Not a miner for any existing chain. Do not use with real funds.**

## What I am asking for
A focused review of the four pieces below, in priority order. A written list of findings is enough; a full report is not required.

| # | File | Size | Why it matters |
|---|------|------|----------------|
| 1 | `src/uuma/wallet/vault.py` | ~90 lines | Encrypts the wallet secret. The only place a password protects a secret. |
| 2 | `src/uuma/manager/stratum.py` | ~90 lines | Network parsing and optional TLS; handles untrusted server input. |
| 3 | `native/uuma_native/uuma_native.c` | ~20 lines | C code called from Python; buffer handling. |
| 4 | `src/uuma/manager/manager.py`, `backend.py` | ~110 lines | Secret handling flow and share verification. |

Out of scope: the PoW phases themselves (`core/phases.py`) are research stand-ins, not claimed to be secure hash constructions, and are not designed to match any existing coin.

## Design as implemented
- **Vault:** scrypt(password, 16-byte random salt; N=2^15, r=8, p=1 by default) gives a 32-byte key, then AES-256-GCM with a random 12-byte nonce. Header fields (version, kdf, n, r, p, salt) are passed as AAD. On load, N must be a power of two in [2^14, 2^20] and r, p must equal 8 and 1. File written atomically, mode 0600. Library: `cryptography` (AESGCM) and stdlib `hashlib.scrypt`.
- **Stratum:** newline-delimited JSON, 64 KiB line cap. Optional TLS through `ssl.create_default_context` with hostname checking. No reconnect, no pinning.
- **Manager:** unlocks the vault, derives a payout label, fetches a job, searches, submits. Backend recomputes every share; it does not trust the submitted digest.

## Specific questions
1. Is the vault construction sound? In particular: AAD coverage (nonce and ciphertext are outside the AAD but are authenticated by GCM itself), the chosen scrypt parameters, and the parameter bounds on load.
2. Passwords are encoded with plain `str.encode()` (UTF-8). There is **no Unicode normalisation**, so the same visible password typed on two systems may not unlock the vault. Should NFKC be applied? What would break for existing vaults?
3. Is there any way a crafted vault file or Stratum message causes excessive memory or CPU beyond the bounds above?
4. `uuma_native.c`: parsing uses `w*y*l`. Is the buffer handling correct for all inputs? Known difference: the pure-Python version accepts arbitrarily large integers for the round index; the C version raises `OverflowError` beyond the platform `long`. Callers only pass small round indices; is this acceptable?
5. Secret lifetime: the mnemonic exists as immutable `bytes` in the manager and is not zeroed. Is the mitigation worth attempting in Python, or should this be documented as a known limit?
6. Ledger records the payout label in clear text. Any privacy concern beyond linking runs to one wallet?

## Known open findings (from my own audit)
No zeroization of secrets; payout label in the ledger; no unlock rate limiting beyond scrypt cost; one secret per vault file; no reconnect or pinning in Stratum.

## How to reproduce the tests
```
pip install -e ".[dev]" setuptools wheel
python setup.py build_ext --inplace
pytest -v
```
The CI workflow does exactly this. Last recorded run: 99 passed (pytest 9.1.1, Python 3.12) in `pytest_output.txt`.

## What has not been verified
The `uuma-manager` command-line tool has never been executed; nothing has been tested against a real chain or pool; no operating system other than Linux (CI) has been used.
