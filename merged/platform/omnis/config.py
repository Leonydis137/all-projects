# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Paths and settings. Everything is overridable through environment variables."""
import os
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parent.parent
SOURCES = Path(os.environ.get("OMNIS_SOURCES", PLATFORM_DIR.parent / "sources")).resolve()
CATALOG = Path(os.environ.get("OMNIS_CATALOG", PLATFORM_DIR / "catalog.json"))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("OMNIS_MODEL", "claude-sonnet-5-5")
API_TOKEN = os.environ.get("OMNIS_API_TOKEN", "")
_raw_database_url = os.environ.get("OMNIS_DATABASE_URL")
if _raw_database_url is not None and not _raw_database_url.strip():
    raise ValueError("OMNIS_DATABASE_URL is set but blank; refusing to fall back to volatile storage")
DATABASE_URL = _raw_database_url.strip() if _raw_database_url is not None else ""

# Static sites served by the gateway: url name -> directory under sources/
STATIC_SITES = {
    "portfolio": "apps/sites/portfolio",
    "jacobsbay": "apps/sites/jacobsbay-site",
    "sat-portal": "apps/web/hybrid-sat-solver-portal",
}
