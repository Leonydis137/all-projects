# OMNIS: Evidence-first integration roadmap

## Objective

OMNIS is the integration layer for the source projects in this repository. The monorepo is the source archive; platform services expose selected capabilities through explicit contracts. A project is not considered integrated merely because it appears in the catalogue.

## Non-negotiable data policy

- Production endpoints must consume caller-supplied or independently retrieved real data.
- No fabricated business records, synthetic research findings, placeholder credentials, or mock integrations may be presented as production results.
- Test fixtures must be isolated from production storage and visibly identified as test-only.
- Missing external credentials or unavailable source systems produce an explicit unavailable/error state. They must never silently fall back to invented data.
- Every research claim must identify its source material, method, assumptions, code revision, environment, and reproducibility instructions.
- A hash proves byte integrity relative to a recorded digest; it does not prove who created the bytes or whether a claim is true.

## Integration boundaries

1. **COVENANT**: policy evaluation and action authorization. Gateway-generated evidence must not be represented as independent source verification.
2. **AEON / autonomous agents**: reasoning and decision services. Agent output is a proposal until validated by policy and evidence.
3. **Quantum Flow / Neural Sovereign / OmniGPT**: user-facing intelligence experiences; integrate behind versioned API contracts rather than merging their UI runtimes blindly.
4. **Project Genesis / CodeEvolve / Codegenie**: controlled research and software-engineering workers. Code execution requires isolated workspaces, resource limits, provenance, and review.
5. **GCD-PvsNP / circuit lower bounds / UUMA**: research workspaces. Hypotheses, proof attempts, computational experiments, and peer-reviewed results must be separate states.
6. **Vantage-ARS / Site Mirror / commerce and static sites**: business and web capabilities remain independently deployable services with explicit data ownership.
7. **Synapse OS and mobile clients**: clients consume authenticated APIs; secrets never ship in mobile binaries.

## Evidence and audit milestones delivered

- Append-only evidence records retain source URI, SHA-256 content digest, timezone-aware acquisition timestamp, acquisition method, declared licence, and submitter. SQLite remains the local default; PostgreSQL is selected explicitly through `OMNIS_DATABASE_URL`.
- PostgreSQL evidence writes and their audit events commit in one transaction. PostgreSQL audit and evidence ledgers are hash chained, append-only, and explicitly verifiable.
- Every `/v1/` request except the read-only `GET /v1/audit` endpoint now receives a request-start audit event before route dispatch and a completion event with the response status. A failed start write blocks route execution; a failed completion write marks the response `X-OMNIS-Audit-Status: incomplete`.
- Request lifecycle events record method, path, and status only; they do not copy request bodies, query strings, or bearer tokens into the audit trail.
- Hash integrity verifies retained records; it does not prove source authenticity or actor identity, and cannot detect deletion of a final suffix without an independently retained checkpoint.

The evidence verification endpoint checks ledger integrity only. Source authenticity remains explicitly unverified until an independent fetcher, signature, or trusted connector validates it.

## Research quality gate

A research result is publishable only when the repository records:
- a falsifiable question and pre-registered method where appropriate;
- raw inputs and their provenance/licensing;
- exact code commit, dependency lock and execution environment;
- deterministic seeds where randomness is methodologically required;
- complete outputs, failed runs and uncertainty estimates;
- independent reproduction and adversarial review.

No claim of a P-vs-NP resolution, new complexity lower bound, or Nobel-level discovery is made by this platform without a valid mathematical proof and independent expert verification.

## Next integration stages

- Add independent source acquisition connectors with strict outbound-network policy and signed provenance attestations; never label a platform signature as independent source authenticity.
- Add PostgreSQL-backed identity, tenancy, permissions, and event processing.
- Split long-running research and agent workloads into isolated workers.
- Integrate each source project only after its own build, tests, licence, secrets, and runtime contract are audited.
- Establish end-to-end tests against real configured services; absent credentials must fail closed.
