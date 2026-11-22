# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Project catalog: every merged repo, what it is, and where its features surface in the platform."""
import json
from functools import lru_cache

from .config import CATALOG

# project path -> how the platform exposes its features
FEATURES = {
    "services/covenant": ["POST /v1/govern", "COVENANT gate on selected decision/recommendation/protocol/assistant actions",
                          "tamper-evident request and decision audit (/v1/audit)"],
    "services/autonomous-ai": ["POST /v1/decide", "POST /v1/recommend"],
    "services/aeon-engine": ["POST /v1/protocols/respond", "POST /v1/protocols/feedback"],
    "tools/self-improving-code-analyzer": ["POST /v1/math/gcd-lcm"],
    "research/circuit-lower-bounds": ["POST /v1/stats/ab", "POST /v1/stats/posterior"],
    "apps/sites/portfolio": ["served at /sites/portfolio"],
    "apps/sites/jacobsbay-site": ["served at /sites/jacobsbay"],
    "apps/web/hybrid-sat-solver-portal": ["served at /sites/sat-portal"],
    "apps/web/omnigpt-web": ["POST /v1/assistant (governed Claude chat)"],
    "apps/web/neural-sovereign": ["POST /v1/assistant (governed Claude chat)"],
}


@lru_cache
def load() -> dict:
    if CATALOG.exists():
        data = json.loads(CATALOG.read_text())
    else:
        data = {"projects": [], "totals": {}}
    for p in data["projects"]:
        p["platform_features"] = FEATURES.get(p["path"], ["standalone (run from merged/sources/" + p["path"] + ")"])
    return data
