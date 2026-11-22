# Covenant-ai import notes

Source repository: https://github.com/Leonydis138/Covenant-ai
Source commit: c9d917b9b258d48b228f131749b56dad352149e0
Source default branch: main
Import date: 2026-11-22

## Reconciliation

The source contains 75 tracked files. The existing `services/covenant/` tree already contains 73 corresponding source paths: 59 byte-identical files and 14 paths whose contents have diverged in the consolidated project. The 14 divergent files were deliberately preserved; they were not overwritten by this import. Two previously absent files have now been added:

- `CONTRIBUTING.md` (copied verbatim)
- `docker-compose.full.yml` (adapted for safer local development)

The compose file is intentionally not byte-identical to the source: hard-coded database and Grafana passwords were replaced with required environment variables, and published ports are bound to loopback. Set `POSTGRES_PASSWORD` and `GF_SECURITY_ADMIN_PASSWORD` before starting it.

## Licensing and claim validation

No standard LICENSE file was found in the source tree. This repository is owned by the same GitHub account as the destination, but a licence should still be selected and documented before external redistribution or accepting third-party contributions.

The source README includes throughput, latency, uptime, and compliance-certification claims. They are source claims, not independently verified results or certifications. Do not present them as validated platform properties without test reports and audit evidence.

## Validation status

This is a source reconciliation/import, not a production deployment approval. Backend/frontend dependencies, Docker services, API contracts, security controls, and test suites still require isolated execution and verification.
