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
- Persistent SQLite evidence ledger with append-only hash chaining.
- Evidence integrity verification that explicitly does not claim source authenticity.

## Run

```bash
cd merged/platform
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn omnis.api:app --host 127.0.0.1 --port 8080
```

Set `OMNIS_API_TOKEN` to protect API routes. Set `OMNIS_EVIDENCE_DB` to select a persistent
evidence database path. The API reports unavailable integrations honestly; it does not
substitute fabricated data when credentials or source systems are absent.

See [OMNIS research and integration roadmap](OMNIS-RESEARCH-AND-INTEGRATION.md).
