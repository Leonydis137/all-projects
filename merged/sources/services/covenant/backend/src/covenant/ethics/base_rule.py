"""Base class for the ten COVENANT commandment rules.

Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>

Reconstructed from how the commandment modules use it: each rule has a
``name``, a ``validate`` check and an ``explain_violation`` message.
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseRule(ABC):
    name: str = "BaseRule"

    @abstractmethod
    def validate(self, action: dict, context: Optional[dict] = None) -> bool:
        """Return True if ``action`` complies with this rule."""

    def explain_violation(self, action: dict, context: Optional[dict] = None) -> str:
        return f"{self.name} violated"
