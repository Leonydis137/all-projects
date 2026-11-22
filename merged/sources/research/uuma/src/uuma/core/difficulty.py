from __future__ import annotations


def meets_difficulty(digest: bytes, required_leading_zero_bits: int) -> bool:
    """True iff digest has >= N leading zero bits.

    N == 0                -> True
    N > len(digest) * 8   -> False
    otherwise             -> top N bits are zero
    """
    if required_leading_zero_bits < 0:
        raise ValueError("difficulty must be non-negative")

    total_bits = len(digest) * 8

    if required_leading_zero_bits == 0:
        return True
    if required_leading_zero_bits > total_bits:
        return False

    value = int.from_bytes(digest, "big")
    return (value >> (total_bits - required_leading_zero_bits)) == 0
