import pytest
from uuma.core.difficulty import meets_difficulty


def test_zero_bits_accepts_anything():
    assert meets_difficulty(b"\xff" * 32, 0)
    assert meets_difficulty(b"\x00" * 32, 0)


def test_all_zero_accepts_up_to_full_width():
    assert meets_difficulty(b"\x00" * 32, 1)
    assert meets_difficulty(b"\x00" * 32, 255)
    assert meets_difficulty(b"\x00" * 32, 256)


def test_over_full_width_rejected():
    assert not meets_difficulty(b"\x00" * 32, 257)


def test_one_leading_bit():
    assert meets_difficulty(b"\x7f" + b"\xff" * 31, 1)
    assert not meets_difficulty(b"\x80" + b"\x00" * 31, 1)


def test_one_byte_of_leading_zeros():
    assert meets_difficulty(b"\x00" + b"\xff" * 31, 8)
    assert not meets_difficulty(b"\x00" + b"\x80" + b"\x00" * 30, 9)


def test_negative_rejected():
    with pytest.raises(ValueError):
        meets_difficulty(b"\x00" * 32, -1)


def test_non_byte_aligned():
    digest = bytes([0x01]) + b"\xff" * 31
    assert meets_difficulty(digest, 7)
    assert not meets_difficulty(digest, 8)
