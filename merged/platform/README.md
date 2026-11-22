# OMNIS - all projects, one platform
Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>

One gateway that combines the features of every repo in this monorepo:
governed actions (COVENANT), decisions, adaptive protocols, recommendations, statistics,
a Claude assistant, a catalog of all 24 projects (4,800+ files analyzed) and static sites - behind one API and one web console.

```bash
cd merged/platform
pip install -r requirements.txt pytest
python -m pytest -q          # 12 tests
uvicorn omnis.api:app --port 8080   # console at http://localhost:8080, API docs at /docs
# or: cp .env.example .env && docker compose up --build
```
Set `ANTHROPIC_API_KEY` to enable `/v1/assistant`, `OMNIS_API_TOKEN` to require a bearer token on `/v1/*`.

Example:
```bash
curl -s localhost:8080/v1/decide -H 'content-type: application/json' -d '{"context":{"risk_level":9}}'
curl -s localhost:8080/v1/decide -H 'content-type: application/json' -d '{"context":{},"attributes":{"harm":3}}'   # 403 blocked by COVENANT
```
See `ARCHITECTURE.md` for how each project is combined. Refresh the catalog with `make catalog`.
