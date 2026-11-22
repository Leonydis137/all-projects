import math

class MathLib:
    def greatest_common_divisor(self, a: int, b: int) -> int:
        if a == 0 and b == 0:
            raise ValueError("GCD(0,0) is undefined.")
        x, y = abs(a), abs(b)
        while y:
            x, y = y, x % y
        return x

    def gcd_of_list(self, numbers: list[int]) -> int:
        if not numbers:
            raise ValueError("List for GCD cannot be empty.")
        result = abs(numbers[0])
        for n in numbers[1:]:
            result = self.greatest_common_divisor(result, n)
        return result

    def calculate_least_common_multiple(self, a: int, b: int) -> int:
        if a == 0 or b == 0:
            return 0
        gcd = self.greatest_common_divisor(a, b)
        return abs(a * b) // gcd

    def lcm_of_list(self, numbers: list[int]) -> int:
        if not numbers:
            raise ValueError("List for LCM cannot be empty.")
        result = abs(numbers[0])
        for n in numbers[1:]:
            result = self.calculate_least_common_multiple(result, n)
        return result

    def is_prime(self, n: int) -> bool:
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        for i in range(3, int(math.isqrt(n)) + 1, 2):
            if n % i == 0:
                return False
        return True

    def factorial(self, n: int) -> int:
        if n < 0:
            raise ValueError("Factorial undefined for negative numbers.")
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result
