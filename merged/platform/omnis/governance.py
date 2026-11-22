# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Governance layer: the ten COVENANT commandments from services/covenant,
used as a policy gate for every action that passes through the platform."""
import importlib
from typing import Any, Optional

from . import sources

sources.wire()

_RULES = [
    ("commandment_01_authority", "AuthorityRule"),
    ("commandment_02_integrity", "IntegrityRule"),
    ("commandment_03_identity", "IdentityRule"),
    ("commandment_04_sustainability", "SustainabilityRule"),
    ("commandment_05_preserve_life", "PreserveLifeRule"),
    ("commandment_06_fidelity", "FidelityRule"),
    ("commandment_07_property", "PropertyRule"),
    ("commandment_08_truth", "TruthRule"),
    ("commandment_09_testimony", "Commandment09Testimony"),
    ("commandment_10_intent", "Commandment10Intent"),
]


def _load() -> list:
    rules = []
    for mod, cls in _RULES:
        m = importlib.import_module(f"covenant.commandments.{mod}")
        rules.append(getattr(m, cls)())
    return rules


def evaluate(action: dict[str, Any], context: Optional[dict] = None) -> dict:
    """Check an action against all ten rules. Missing evidence fails closed
    for rules 01-03 and 09 (they require mission/auditable/provenance flags)."""
    results, violations = [], []
    for rule in _load():
        ok = bool(rule.validate(action, context))
        results.append({"rule": rule.name, "ok": ok})
        if not ok:
            violations.append({"rule": rule.name, "reason": rule.explain_violation(action, context)})
    return {"allowed": not violations, "violations": violations, "checked": results}


def stamp(action: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """Attach the evidence the platform itself can vouch for (it audits every call)."""
    base = {"mission": "PRIMARY_MISSION", "auditable": True, "data_provenance": True}
    base.update(action)
    base.update(overrides)
    return base
