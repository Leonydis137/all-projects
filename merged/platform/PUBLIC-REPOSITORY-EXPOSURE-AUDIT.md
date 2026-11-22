# Public repository exposure audit

Date: 2026-11-22
Audited ref: integration/omnis-evidence-foundation
Audited commit: 8b9ada59b046face1a4792bea60e672d6a9ca8ab
Destination visibility: public

## Findings

The repository tree contains two tracked, non-example dotenv files with non-empty values:

- `apps/web/codeevolve-ai/.env` — contains a populated `DATABASE_URL` setting.
- `apps/web/omnigpt-web/.env` — contains a populated `VITE_OPENAI_API_KEY` setting.

The values are deliberately not reproduced in this report. Treat both credentials as compromised because the files are present in a public repository. Rotate/revoke the database credential and API key with their respective providers, then update deployment secrets outside Git. Removing a file from the latest tree does not remove it from Git history or existing clones/caches.

The tree also contains a tracked SQLite database at `apps/web/project-genesis/agent_experience.db`. Its contents have not been inspected; it is quarantined from the current tree pending data-owner review.

Generated or cache material observed:

- `apps/mobile/synapse-os/.build-outputs/app-debug.apk` (11,542,281 bytes)
- `apps/sites/jacobsbay-site/hts-cache/doit.log`
- `apps/sites/jacobsbay-site/hts-cache/new.zip`

## Remediation applied in this branch

The non-example dotenv files, SQLite database, Android build output, and website mirroring cache have been removed from the current branch tree. This is a tip-of-branch cleanup only, not a history purge.

## Required owner actions

1. Immediately revoke/rotate the database credential and API key identified above.
2. Review the SQLite database and any previously committed archives/logs for personal, customer, or production data.
3. Decide whether to perform a coordinated Git history rewrite to purge exposed secrets and sensitive data. Coordinate with collaborators first; rotating credentials is mandatory even if history is rewritten.
4. Keep the destination private if proprietary project material is not intended for public release. The repository remains public at the time of this audit.

## Limitations

This was a tracked-tree filename/content-shape audit, not a full forensic secret scan of every historical commit, binary, archive, Git LFS object, release asset, fork, or cached clone. Absence from this report is not proof that a secret is absent.
