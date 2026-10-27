import pytest

from app.exceptions import InvalidInputError
from app.input_validators import normalize_command, parse_number


@pytest.mark.parametrize("value, expected", [("2", 2.0), (" -3.5 ", -3.5), ("0", 0.0)])
def test_parse_number_accepts_finite_values(value, expected):
    assert parse_number(value) == expected


@pytest.mark.parametrize("value", ["abc", "", "nan", "inf", "-inf"])
def test_parse_number_rejects_invalid_or_non_finite_values(value):
    with pytest.raises(InvalidInputError):
        parse_number(value)


def test_parse_number_enforces_configured_maximum():
    assert parse_number("-10", max_value=10) == -10
    with pytest.raises(InvalidInputError, match="must not exceed"):
        parse_number("10.01", max_value=10)


def test_normalize_command_strips_and_lowercases():
    assert normalize_command("  ROOT  ") == "root"
