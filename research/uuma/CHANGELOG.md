# Changelog
Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>

## Unreleased
- Native C helper `uuma_native.mix_buffer` for the memory-hard phase (optional; pure Python remains the reference) + parity tests + A/B benchmark.
- `wallet/vault.py`: scrypt + AES-256-GCM encrypted vault with header authentication, atomic 0600 saves, `rekey`.
- `manager/`: chain registry (only `uuma-dryrun` implemented), independent share-verifying dry-run backend, manager, CLI.
- `manager/stratum.py`: Stratum V1 framing + client with optional verified TLS (local-server tested; no pool).
- `.github/workflows/tests.yml`: full pytest run on GitHub Actions (untested until first push).
- README benchmark table synced to the current `bench/m1_benchmark.json`.
- Console: navigation, pipeline explainer, status table, code map, theme toggle, copy buttons.
- Fix: ledger file created 0600 from the start; dry-run backend made thread-safe.
- `docs/AUDIT.md`: decisions, findings, verification status.
- Not implemented: Stratum V2, real pool integration, all real chain backends, M4-M9. No external cryptographic review.
