# OMNIS architecture
Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>

```
merged/
├── sources/    verbatim copy of every project (never edited - originals stay runnable)
└── platform/   the new combined project
    └── omnis/
        ├── api.py          FastAPI gateway - single entry point, serves the console
        ├── governance.py   COVENANT commandments (imported from sources/services/covenant)
        ├── audit.py        hash-chained audit log of every governed call
        ├── decision.py     data-driven rule engine   (generalises services/autonomous-ai)
        ├── protocols.py    adaptive protocols, no Tk (generalises services/aeon-engine)
        ├── recommend.py    k-NN recommender, numpy only (from services/autonomous-ai)
        ├── stats.py        Bayesian A/B + analyzers (from research/circuit-lower-bounds)
        ├── mathops.py      MathLib (imported from tools/self-improving-code-analyzer)
        ├── assistant.py    Claude chat behind the gate (concept from OmniGPT / Neural Sovereign)
        ├── inventory.py    static analysis of all of sources/ -> catalog.json
        └── catalog.py      project catalog + where each project's features surface
```

## Flow of a governed request
client -> `api.py` -> `gated()` stamps platform evidence (mission, auditable, provenance) and merges
client attributes (harm, intent...) -> 10 commandments -> audit entry -> allowed? run feature : HTTP 403.
Clients cannot override the three evidence fields.

## How each source project is combined
| Source | Mode | Result |
|---|---|---|
| services/covenant | imported unchanged (path wiring in `sources.py`) | governance gate, 10 rules |
| tools/self-improving-code-analyzer | imported unchanged | `/v1/math/gcd-lcm` |
| research/circuit-lower-bounds | imported if deps present; Bayesian logic re-implemented | `/v1/stats/*` |
| services/autonomous-ai | re-implemented cleanly (originals have syntax errors / pandas+sklearn deps) | `/v1/decide`, `/v1/recommend` |
| services/aeon-engine | re-implemented headless (original is a Tkinter GUI) | `/v1/protocols/*` |
| apps/sites/*, hybrid-sat-solver-portal | served as static mounts | `/sites/<name>` |
| OmniGPT / Neural Sovereign idea | new `assistant.py` | `/v1/assistant` |
| everything else (Vantage, Quantum Flow OS, Site Mirror, Android/Expo apps, Codegenie, UUMA, ...) | cataloged + analyzed, run standalone | `/v1/catalog`, `/v1/inventory` |

## Deliberately not wired
- **UUMA** (mining framework): catalogued only; no mining is started by the platform.
- Heavy standalone apps (Site Mirror, Vantage, Quantum Flow OS): need their own build/runtime; they are listed with their stack and size rather than embedded.
- Known broken sources found by the analyzer: `services/autonomous-ai` (3 files with syntax errors) and `research/circuit-lower-bounds` (1) - see `GET /v1/inventory`.
