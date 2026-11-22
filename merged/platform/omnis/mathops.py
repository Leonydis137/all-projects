# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Number theory helpers from tools/self-improving-code-analyzer (MathLib)."""
from . import sources

sources.wire()


def lib():
    from mathlib_core.mathlib import MathLib
    return MathLib()


def gcd_lcm(numbers: list[int]) -> dict:
    m = lib()
    return {"gcd": m.gcd_of_list(numbers), "lcm": m.lcm_of_list(numbers)}
