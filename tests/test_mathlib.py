from mathlib_core.mathlib import MathLib

def test_gcd():
    assert MathLib().greatest_common_divisor(48, 18) == 6

def test_lcm():
    assert MathLib().lcm_of_list([2, 3, 4]) == 12

def test_prime():
    assert MathLib().is_prime(11)
    assert not MathLib().is_prime(10)

def test_factorial():
    assert MathLib().factorial(5) == 120
