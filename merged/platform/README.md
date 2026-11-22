# OMNIS - all projects, one platform

Author: Juan-Louw Greyling

OMNIS is the integration gateway for this monorepo. The original projects remain under
`merged/sources/`; the platform exposes selected capabilities through versioned APIs.
A catalogue entry is not a claim that a project is fully integrated or production-ready.

## Current gateway capabilities

- COVENANT policy evaluation and governed decision routes.
- AEON protocol endpoint and decision rules.
- Project inventory and source catalogue.
- Statistical and mathematical endpoints.
- Optional external-model assistant (requires an explicitly configured provider key).
- Append-only evidence ledger with hash-chain verification.
- SQLite remains the default evidence store; PostgreSQL is selected only when
  `OMNIS_DATABASE_URL` is explicitly configured.

## Run

```bash
cd merged/platform
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn omnis.api:app --host 127.0.0.1 --port 8080
```

Set `OMNIS_API_TOKEN` to protect API routes. Without `OMNIS_DATABASE_URL`, OMNIS uses
the persistent SQLite database selected by `OMNIS_EVIDENCE_DB`. To use PostgreSQL,
apply migrations 001, 002, 003, and 004 in order using a database-owner/migration role, then set `OMNIS_DATABASE_URL` to a PostgreSQL
DSN for a dedicated runtime role with schema USAGE and SELECT/INSERT privileges only.
Remote connections require certificate and hostname verification (`sslmode=verify-full`);
configure the provider CA as the libpq root certificate. The runtime never runs schema
migrations automatically. Export and verify existing SQLite evidence before switching;
setting the PostgreSQL URL does not automatically copy the SQLite records. Supply an optional
`idempotency_key` on evidence submissions to make client retries return the original row;
reusing a key with different record content is rejected.

PostgreSQL adapter integration tests run when `OMNIS_TEST_DATABASE_URL` is set.
The API reports unavailable integrations honestly; it does not substitute fabricated
data when credentials or source systems are absent.

Both evidence and audit events use PostgreSQL when `OMNIS_DATABASE_URL` is configured.
The evidence insert and its corresponding audit event share one transaction, so an
audit failure rolls back the evidence insert. Optional client idempotency keys make
evidence retries safe; reusing a key with different content is rejected.

Health probes validate the latest ledger entries without scanning full history.
Use the explicit evidence and audit verification operations for full-chain checks.
Hash integrity does not prove source authenticity or actor identity and cannot
independently detect deletion of a final suffix without an external checkpoint.
Existing SQLite evidence and in-memory audit history are not automatically migrated;
export, import, and verify historical records before switching storage.
