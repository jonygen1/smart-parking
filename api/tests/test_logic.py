import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from logic import calc_price, is_palindrome_plate, normalize_plate  # noqa: E402


def test_normalize_7_digits():
    assert normalize_plate("1234567") == "12-345-67"


def test_normalize_8_digits_with_spaces():
    assert normalize_plate("123 45 678") == "123-45-678"


def test_normalize_already_dashed():
    assert normalize_plate("12-345-67") == "12-345-67"


@pytest.mark.parametrize("bad", ["", "123", "abcdefg", "123456789", None])
def test_normalize_rejects_bad_plates(bad):
    with pytest.raises(ValueError):
        normalize_plate(bad)


def test_price_first_unit_even_after_one_second():
    assert calc_price(0, 1, 3600, 15, 10) == (1, 15)


def test_price_exactly_one_hour_is_still_one_unit():
    assert calc_price(0, 3600, 3600, 15, 10) == (1, 15)


def test_price_started_second_hour_is_charged():
    assert calc_price(0, 3601, 3600, 15, 10) == (2, 25)


def test_palindrome_parks_free():
    assert is_palindrome_plate("12-345-21") is False
    assert is_palindrome_plate("12-343-21") is True
    assert calc_price(0, 99999, 3600, 15, 10, plate="12-343-21") == (0, 0)
