# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Statistics: Bayesian analysis from research/circuit-lower-bounds (loaded from sources)
plus lightweight helpers that work with numpy only."""
import math
from typing import Optional

from . import sources

sources.wire()


def posterior(bayes_factor: float, prior: float = 0.5) -> float:
    """Posterior probability of H1 from a Bayes factor and prior."""
    odds = bayes_factor * prior / (1 - prior)
    return odds / (1 + odds)


def interpret_bayes_factor(bf: float) -> str:
    if bf < 1:
        return "evidence favours H0"
    for limit, label in ((3, "anecdotal"), (10, "moderate"), (30, "strong"), (100, "very strong")):
        if bf < limit:
            return f"{label} evidence for H1"
    return "decisive evidence for H1"


def ab_test(conv_a: int, n_a: int, conv_b: int, n_b: int, prior_strength: float = 1.0, draws: int = 20000, seed: Optional[int] = 0) -> dict:
    """Beta-binomial A/B test: P(B beats A) by Monte-Carlo."""
    import numpy as np

    rng = np.random.default_rng(seed)
    a = rng.beta(prior_strength + conv_a, prior_strength + n_a - conv_a, draws)
    b = rng.beta(prior_strength + conv_b, prior_strength + n_b - conv_b, draws)
    return {
        "p_b_beats_a": float((b > a).mean()),
        "rate_a": conv_a / n_a, "rate_b": conv_b / n_b,
        "expected_lift": float((b / a - 1).mean()),
    }


def research_analyzers() -> dict:
    """Expose the original BayesianAnalyzer/PowerAnalyzer classes if their deps are installed."""
    try:
        import validation  # research/circuit-lower-bounds/validation.py
        return {"available": True, "classes": ["BayesianAnalyzer", "PowerAnalyzer"], "module": validation.__file__}
    except Exception as e:  # missing statsmodels etc.
        return {"available": False, "error": f"{type(e).__name__}: {e}"}


def entropy(values: list[float]) -> float:
    total = sum(values)
    return -sum((v / total) * math.log2(v / total) for v in values if v > 0) if total else 0.0
