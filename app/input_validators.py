"""Validation helpers for calculator REPL inputs."""

import math

from .exceptions import InvalidInputError


def parse_number(value: str, max_value: float = float("inf")) -> float:
    """Parse a finite floating-point value or raise a user-facing error."""
    try:
        number = float(value)
    except ValueError as error:
        raise InvalidInputError(f"Invalid number: {value}") from error
    if not math.isfinite(number):
        raise InvalidInputError("Number must be finite.")
    if abs(number) > max_value:
        raise InvalidInputError(f"Number must not exceed {max_value} in magnitude.")
    return number


def normalize_command(value: str) -> str:
    """Normalize a command or operator token."""
    return value.strip().lower()