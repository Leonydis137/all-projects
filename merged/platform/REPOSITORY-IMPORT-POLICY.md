# Repository import and visibility policy

The current destination repository, Leonydis138/all-projects, is public. The account inventory contains private source repositories as well as public repositories.

A public destination changes the confidentiality of every file copied into it. Therefore:

- Public source repositories may be audited for consolidation and imported subject to licence and provenance review.
- Private source repository contents must not be copied into this public destination until the owner explicitly chooses a safe visibility outcome.
- The safe options are to make the destination private before importing private source contents, or to explicitly authorize publication of those contents after reviewing their licences and secrets.
- Repository names and metadata are not equivalent to source-code access permission.
- Never copy .env files, credentials, private keys, access tokens, production database dumps, customer data, or unredacted logs.
- Preserve original repositories until consolidated equivalents have been verified and a rollback plan exists.

The GitHub account inventory currently reports 53 repositories including the destination. The existing monorepo catalogue describes 24 active source projects; it is not proof that every account repository has been imported. Several small, empty, duplicate-version, private, and experimental repositories still require individual classification.

No private source contents have been copied by this integration branch.