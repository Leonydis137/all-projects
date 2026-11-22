# Consolidation execution decision — public-only phase

Date: 2026-11-22

## Execution mode

The owner has instructed the integration to continue without changing the current repository visibility. The destination, `Leonydis138/all-projects`, is still public. Accordingly, this phase is **public-source-only**.

- Public source repositories may be inventoried and reviewed for import.
- Private source repository contents are excluded while the destination remains public.
- No private source code, configuration, history, or assets are to be copied into this destination in this phase.
- Repository metadata may be used to identify excluded repositories, but metadata is not source-content authorization.
- Do not copy credentials, tokens, private keys, `.env` files, production data, customer data, or unredacted logs from any source.
- Do not merge an import solely because it builds; check licence, provenance, secrets, dependencies, runtime, and data ownership first.
- Preserve source repositories and history; do not delete or rewrite originals.

## Inventory snapshot

The connected GitHub inventory returned 53 repositories for this owner, including this destination: 43 public and 10 private. The existing monorepo catalogue contains 24 active project entries. These are different counts: a catalogue entry is not proof that a repository has been fully imported, and a repository can contain multiple projects.

Private repositories observed in the inventory (excluded from source-content import in this phase):

- `jacobsbayaccomodation` (empty)
- `Jacobsbay-Accomodation`
- `omnigpt-web`
- `SA-Threads---Premier-Online-Fashion`
- `Nexus` (empty)
- `Covenant-ai`
- `neural_sovereign`
- `Site-Mirror` (empty)
- `uuma`
- `combined-repositories` (empty)

The inventory snapshot is time-bound and should be refreshed before each import batch.

## Validation gate

Every candidate public repository must pass these checks before import:

1. Confirm default branch and inspect the complete file tree.
2. Identify licence and preserve required notices; if no licence is declared, do not assume permission to relicense or redistribute.
3. Scan tracked files and history for secrets and sensitive data; quarantine findings rather than copying them.
4. Identify duplicate, superseded, empty, generated, vendored, and binary content.
5. Record source repository, commit SHA, import timestamp, and destination path.
6. Preserve project-specific build/test commands and report unsupported environments explicitly.
7. Run project tests in isolation, then platform integration tests; no green status may be claimed without successful runs.

## Current integration branch

The OMNIS evidence-first foundation remains on `integration/omnis-evidence-foundation` under draft PR #4. Its latest observed CI run failed in the `detect` and `platform` jobs; the failure details were not available through the connected GitHub interface. Do not merge this PR until the failure is diagnosed and CI passes.

This phase makes no claim that every public repository is already integrated, that the platform is production-ready, or that any mathematical or scientific conjecture has been resolved.
