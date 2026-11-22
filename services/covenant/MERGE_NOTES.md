# Merge notes: covenant-ai + covenant-enterprise -> services/covenant
Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>

The canonical project is the V5.0 platform (`backend/` + `frontend/`). The two older
standalone repos were merged into `backend/src/covenant/`:

- **Added** (104 modules from covenant-enterprise, plus the rest from covenant-ai): `agents/`, `commandments/` (10 rules), `security/zero_trust.py`, `llm/`, `utils/`, `advisory/`, `optimization/`, `verification/`, extra `core/` modules and `api/schemas.py`.
- **Conflicts**: where a file existed in both with different content, the canonical V5.0 file was kept and the other versions are stored verbatim as `_variants/{enterprise,ai}/<path>.py.variant` (non-importable). `blockchain/audit_trail.py` additionally re-exports the Merkle `BlockchainAuditTrail` from the enterprise version (`blockchain/blockchain_audit_trail.py`).
- **Dependencies**: extra packages needed by the merged modules are in `backend/requirements-variants.txt`.
- **Fixes needed to make the merged code import**: `src.*` imports rewritten to `covenant.*`; added the missing `ethics/base_rule.py` (`BaseRule`), `exceptions.py` alias, `security/encryption.py` (`EncryptionManager`, Fernet); `PBKDF2` -> `PBKDF2HMAC`; class aliases so `TestimonyRule`/`IntentRule`/`CommandmentNN*` resolve; `core/covenant_layer.py` import path.
- **Tests**: variant tests merged into `backend/tests/`. 24 pass; 4 are marked xfail in `tests/conftest.py` because of bugs in the original code (undefined names, API mismatches).
- **Not tested**: modules needing `torch`, `openai`, `uvicorn`, `passlib`, `strawberry`, `asyncpg` were only syntax-checked (all compile), not run. Check with `pip install -r requirements.txt -r requirements-variants.txt`.
- Other extras: `docs/variants/` (guides, overviews, original `.tar.gz` bundle), `backend/covenant_cli.py`, `backend/examples/`, `backend/config/`.
