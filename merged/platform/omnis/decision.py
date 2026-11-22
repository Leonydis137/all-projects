# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Rule-based decision engine. Generalises services/autonomous-ai DecisionEngine:
rules are data (field/operator/value), so they can be created over the API,
and every decision is passed through the governance gate."""
import operator
from dataclasses import dataclass, field
from typing import Any

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}


@dataclass
class Rule:
    name: str
    field: str
    op: str
    value: Any
    action: str
    priority: int = 0

    def matches(self, ctx: dict) -> bool:
        if self.field not in ctx or self.op not in OPS:
            return False
        try:
            return bool(OPS[self.op](ctx[self.field], self.value))
        except TypeError:
            return False


@dataclass
class DecisionEngine:
    rules: list[Rule] = field(default_factory=list)

    def add_rule(self, rule: Rule) -> None:
        if rule.op not in OPS:
            raise ValueError(f"unsupported operator {rule.op!r}; use one of {sorted(OPS)}")
        self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.priority)

    def decide(self, ctx: dict) -> dict:
        for r in self.rules:
            if r.matches(ctx):
                return {"action": r.action, "rule": r.name}
        return {"action": None, "rule": None}


def default_engine() -> DecisionEngine:
    e = DecisionEngine()
    e.add_rule(Rule("high-risk-alert", "risk_level", ">", 7, "alert", priority=10))  # from autonomous-ai
    e.add_rule(Rule("medium-risk-review", "risk_level", ">", 4, "review", priority=5))
    return e
