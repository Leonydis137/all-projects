# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Paths and settings. Everything is overridable through environment variables."""
import os
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parent.parent
SOURCES = Path(os.environ.get("OMNIS_SOURCES", PLATFORM_DIR.parent / "sources")).resolve()
CATALOG = Path(os.environ.get("OMNIS_CATALOG", PLATFORM_DIR / "catalog.json"))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("OMNIS_MODEL", "claude-sonnet-5-5")
API_TOKEN = os.environ.get("OMNIS_API_TOKEN", "")  # if set, required as Bearer token on /v1/*

# Static sites served by the gateway: url name -> directory under sources/
STATIC_SITES = {
    "portfolio": "apps/sites/portfolio",
    "jacobsbay": "apps/sites/jacobsbay-site",
    "sat-portal": "apps/web/hybrid-sat-solver-portal",
}
