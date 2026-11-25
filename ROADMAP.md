# Repository roadmap

This roadmap describes the next engineering stages for the unified monorepo. Work is sequenced by dependency and risk; a phase is complete only when its acceptance criteria are met and recorded in the repository.

## 1. CI and repository integrity

**Objective:** make the root catalog the single source of truth and ensure CI reports real failures.

- [x] Point GitHub Actions at the root `projects.json` and `scripts/projects.sh`.
- [x] Validate every catalog entry, supported project kind, and resolved project directory.
- [x] Propagate failures across all selected projects instead of allowing a pipeline/subshell to return success.
- [x] Cover Node, Expo, pnpm, Python, static-site, and Android catalog entries with the appropriate validation path.
- [ ] Add deterministic lockfiles and pinned toolchains to projects that currently rely on floating dependency resolution.
- [ ] Add per-project test/build capability metadata so CI can distinguish a real test run from an intentional skip.
- [ ] Establish a scheduled full validation run and retain machine-readable test artifacts.

**Exit criteria:** a deliberately failing project command fails the workflow; catalog drift fails before matrix execution; skipped checks are labelled and never reported as passed tests.

## 2. OMNIS platform reliability

**Objective:** preserve tenant isolation and durable evidence while improving operational confidence.

- [ ] Execute the complete PostgreSQL migration sequence against a clean PostgreSQL 16 database in CI, including migration 004's non-transactional index creation.
- [ ] Expand integration coverage for tenant identity, actor-attributed audit events, evidence writes, assistant conversations, and usage metering.
- [ ] Verify quota enforcement under concurrent requests and prove failed/rolled-back requests do not double-charge usage.
- [x] Evaluate minute/month boundaries using one wall-clock decision timestamp captured after the per-tenant metering lock, and persist that same timestamp to usage events and counters.
- [ ] Add backup/restore and evidence-chain verification procedures with a tested recovery exercise.
- [ ] Add operational health signals for database readiness, migration compatibility, and storage durability without exposing sensitive internals.

**Exit criteria:** clean-database migrations and tenant-isolation tests run in CI; restore and integrity checks are reproducible from documented commands.

## 3. Project integration and ownership

**Objective:** turn the catalog into a reliable map of the maintained monorepo rather than a list of copied directories.

- [ ] Assign each catalog entry an owner, lifecycle state, and supported commands.
- [ ] Identify duplicate originals under `merged/sources` versus maintained root paths; document the canonical location for each project.
- [ ] Remove stale generated artifacts, copied dependency trees, and accidental build outputs after owner review.
- [ ] Standardize environment examples, secret handling, contribution instructions, and license metadata.
- [ ] Add repository-wide checks for oversized files, committed databases, secrets, and generated artifacts.

**Exit criteria:** every active project has a canonical path, an owner, a reproducible setup path, and an explicit test/build status.

## 4. Release and operational governance

**Objective:** make changes traceable and releases repeatable.

- [ ] Adopt pull-request templates with scope, risk, migration, test evidence, and rollback sections.
- [ ] Define versioning and release notes for OMNIS and independently deployable applications.
- [ ] Add dependency update automation with lockfile review and CI gates.
- [ ] Document incident response, security reporting, and release rollback ownership.

**Exit criteria:** a release can be built, verified, deployed, and rolled back using repository documentation alone.

## Current constraints

- The Android catalog entries currently have Gradle build files but no checked-in Gradle wrapper, so CI validates their build inputs and explicitly defers compilation until a wrapper is committed.
- Static projects are checked for an HTML entry point; this is structural validation, not a browser-based functional test.
- A successful dependency installation or a command ending in `--if-present` is not evidence that a project has a test suite. Project-level test capability metadata remains an outstanding task.
- OMNIS PostgreSQL integration remains a separate CI job because it requires a PostgreSQL service and the platform's migration/test environment.
