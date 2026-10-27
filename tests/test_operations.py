import pytest

from app.exceptions import InvalidOperationError
from app.operations import OperationFactory, Operations


@pytest.mark.parametrize(
    "operation, first_number, second_number, expected_result",
    [
        (Operations.addition, 2, 3, 5),
        (Operations.addition, -2, 3, 1),
        (Operations.addition, 0, 4, 4),
        (Operations.addition, 2.5, 1.5, 4.0),
        (Operations.subtraction, 5, 3, 2),
        (Operations.subtraction, -2, 3, -5),
        (Operations.subtraction, 0, 4, -4),
        (Operations.subtraction, 5.5, 2.5, 3.0),
        (Operations.multiplication, 2, 3, 6),
        (Operations.multiplication, -2, 3, -6),
        (Operations.multiplication, 0, 4, 0),
        (Operations.multiplication, 2.5, 2, 5.0),
        (Operations.division, 6, 3, 2),
        (Operations.division, -6, 3, -2),
        (Operations.division, 0, 4, 0),
        (Operations.division, 7.5, 2.5, 3.0),
        (Operations.modulus, 7, 3, 1),
        (Operations.modulus, -7, 3, 2),
        (Operations.integer_division, 7, 3, 2),
        (Operations.integer_division, -7, 3, -2),
        (Operations.percentage, 25, 200, 12.5),
        (Operations.absolute_difference, 3, 8, 5),
        (Operations.absolute_difference, 8, 3, 5),
        (Operations.power, 2, 3, 8),
        (Operations.power, 2, -2, 0.25),
        (Operations.power, -2, 3, -8),
        (Operations.power, 2, 0, 1),
        (Operations.root, 9, 2, 3),
        (Operations.root, 27, 3, 3),
        (Operations.root, -8, 3, -2),
        (Operations.root, 0, 2, 0),
    ],
)
def test_operations_with_numeric_values(
    operation, first_number, second_number, expected_result
):
    assert operation(first_number, second_number) == expected_result


def test_division_by_zero():
    with pytest.raises(ValueError, match="divide by zero"):
        Operations.division(6, 0)


def test_root_rejects_zero_degree():
    with pytest.raises(ValueError, match="Root degree cannot be zero"):
        Operations.root(9, 0)


@pytest.mark.parametrize(
    "operation",
    [Operations.modulus, Operations.integer_division, Operations.percentage],
)
def test_division_based_operations_reject_zero_denominator(operation):
    with pytest.raises(ValueError, match="zero"):
        operation(6, 0)


@pytest.mark.parametrize("degree", [2, 2.5])
def test_root_rejects_non_real_negative_roots(degree):
    with pytest.raises(ValueError, match="negative number requires an odd"):
        Operations.root(-9, degree)


@pytest.mark.parametrize(
    "operator, first_number, second_number, expected_result",
    [
        ("+", 2, 3, 5),
        ("-", 5, 3, 2),
        ("*", 2, 3, 6),
        ("/", 6, 3, 2),
        ("%", 7, 3, 1),
        ("//", -7, 3, -2),
        ("percent", 25, 200, 12.5),
        ("abs_diff", 3, 8, 5),
        ("^", 2, 3, 8),
        ("root", 27, 3, 3),
    ],
)
def test_operation_factory_creates_executable_strategies(
    operator, first_number, second_number, expected_result
):
    strategy = OperationFactory.create(operator)

    assert strategy.execute(first_number, second_number) == expected_result
    assert OperationFactory.supports(operator)


def test_operation_factory_rejects_unknown_strategy():
    assert not OperationFactory.supports("unknown")
    with pytest.raises(InvalidOperationError, match="Unsupported operation"):
        OperationFactory.create("unknown")
