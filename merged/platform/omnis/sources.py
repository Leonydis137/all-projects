# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Makes code from the copied repos importable without modifying it."""
import sys

from .config import SOURCES

# folder under sources/ that must be on sys.path -> what it provides
IMPORT_ROOTS = [
    "services/covenant/backend/src",       # covenant.* (commandments, engines)
    "tools/self-improving-code-analyzer",  # mathlib_core
    "research/circuit-lower-bounds",       # validation (Bayesian / power analysis)
]


def wire() -> list[str]:
    added = []
    for rel in IMPORT_ROOTS:
        p = str(SOURCES / rel)
        if (SOURCES / rel).is_dir() and p not in sys.path:
            sys.path.append(p)
            added.append(rel)
    return added
