import pytest
from datetime import datetime

from app.calculation import Calculation, CalculationFactory
from app.history import CalculationHistory


@pytest.mark.parametrize(
    "operator, first_number, second_number, expected_result",
    [
        ("+", 2, 3, 5),
        ("-", 5, 3, 2),
        ("*", 2, 3, 6),
        ("/", 6, 3, 2),
        ("^", 2, 3, 8),
        ("root", 27, 3, 3),
    ],
)
def test_factory_creates_calculation_instances(
    operator, first_number, second_number, expected_result
):
    calculation = CalculationFactory.create(
        operator, first_number, second_number
    )

    assert isinstance(calculation, Calculation)
    assert calculation.perform() == expected_result


@pytest.mark.parametrize("operator", ["+", "-", "*", "/", "^", "root"])
def test_factory_supports_basic_operators(operator):
    assert CalculationFactory.supports(operator)


def test_factory_rejects_unsupported_operator():
    with pytest.raises(ValueError, match="Unsupported operation: unknown"):
        CalculationFactory.create("unknown", 2, 3)


def test_factory_reports_unsupported_operator():
    assert not CalculationFactory.supports("unknown")


def test_history_starts_empty(tmp_path):
    history = CalculationHistory(tmp_path / "history.csv")

    assert history.get_all() == ()
    assert history.format_entries() == "No calculations yet."


def test_history_stores_and_formats_calculations(tmp_path):
    history = CalculationHistory(tmp_path / "history.csv", auto_save=False)
    first_calculation = CalculationFactory.create("+", 2, 3)
    second_calculation = CalculationFactory.create("*", 4, 5)
    first_calculation.perform()
    second_calculation.perform()

    history.add(first_calculation)
    history.add(second_calculation)

    assert history.get_all() == (
        {
            "first_operand": 2,
            "operator": "+",
            "second_operand": 3,
            "result": 5,
            "timestamp": first_calculation.timestamp,
        },
        {
            "first_operand": 4,
            "operator": "*",
            "second_operand": 5,
            "result": 20,
            "timestamp": second_calculation.timestamp,
        },
    )
    assert datetime.fromisoformat(first_calculation.timestamp).utcoffset().total_seconds() == 0
    assert history.format_entries() == "1. 2 + 3 = 5\n2. 4 * 5 = 20"


def test_calculation_string_representation():
    calculation = CalculationFactory.create("+", 2, 3)
    calculation.perform()

    assert str(calculation) == "2 + 3 = 5"