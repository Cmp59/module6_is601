import pandas as pd
import pytest

from app.calculator import Calculator
from app.calculator_config import CalculatorConfig
from app.exceptions import InvalidInputError, InvalidOperationError


def make_calculator(tmp_path, auto_save=True):
    return Calculator(
        CalculatorConfig(tmp_path / "history.csv", auto_save=auto_save)
    )


def test_calculator_facade_calculates_and_notifies_history(tmp_path):
    calculator = make_calculator(tmp_path)

    result = calculator.calculate("+", 2, 3)

    assert result == 5
    assert "2 + 3 = 5" in calculator.history_text()
    assert calculator.session_history_file.exists()


def test_calculator_facade_rejects_unknown_operation(tmp_path):
    calculator = make_calculator(tmp_path)

    with pytest.raises(InvalidOperationError, match="Unsupported operation"):
        calculator.calculate("unknown", 2, 3)


def test_calculator_applies_precision_and_logs_calculation(tmp_path):
    calculator = Calculator(
        CalculatorConfig(
            tmp_path / "history.csv",
            auto_save=False,
            precision=2,
        )
    )

    assert calculator.calculate("divide", 1, 3) == 0.33
    calculator.close()

    log_text = calculator.config.log_file.read_text(encoding="utf-8")
    assert "Calculation: 1 divide 3 = 0.33" in log_text


def test_calculator_rejects_input_over_configured_maximum(tmp_path):
    calculator = Calculator(
        CalculatorConfig(
            tmp_path / "history.csv",
            auto_save=False,
            max_input_value=10,
        )
    )

    with pytest.raises(InvalidInputError, match="exceeds the maximum"):
        calculator.calculate("add", 11, 1)


def test_calculator_rejects_nonnumeric_api_input(tmp_path):
    calculator = make_calculator(tmp_path, auto_save=False)

    with pytest.raises(InvalidInputError, match="Inputs must be numeric"):
        calculator.calculate("add", "not numeric", 1)


def test_calculator_undo_redo_and_empty_stack_results(tmp_path):
    calculator = make_calculator(tmp_path, auto_save=False)

    assert calculator.undo() is False
    assert calculator.redo() is False
    calculator.calculate("+", 2, 3)
    assert calculator.undo() is True
    assert calculator.history_text() == "No calculations yet."
    assert calculator.undo() is False
    assert calculator.redo() is True
    assert "2 + 3 = 5" in calculator.history_text()
    assert calculator.redo() is False


def test_calculator_new_calculation_clears_redo_stack(tmp_path):
    calculator = make_calculator(tmp_path, auto_save=False)
    calculator.calculate("+", 1, 2)
    calculator.undo()
    calculator.calculate("*", 3, 4)

    assert calculator.redo() is False
    assert "3 * 4 = 12" in calculator.history_text()


def test_calculator_clear_resets_history_and_undo_redo(tmp_path):
    calculator = make_calculator(tmp_path, auto_save=False)
    calculator.calculate("+", 2, 3)

    removed_count = calculator.clear()

    assert removed_count == 1
    assert calculator.history_text() == "No calculations yet."
    assert calculator.undo() is False
    assert calculator.redo() is False


def test_calculator_saves_and_loads_history(tmp_path):
    calculator = make_calculator(tmp_path, auto_save=False)
    calculator.calculate("^", 2, 3)
    calculator.save()
    pd.DataFrame(
        [[9, "+", 1, 10]],
        columns=["first_operand", "operator", "second_operand", "result"],
    ).to_csv(calculator.session_history_file, index=False)

    calculator.load()

    assert "9 + 1 = 10" in calculator.history_text()
    assert calculator.undo() is True
    assert "2 ^ 3 = 8" in calculator.history_text()


def test_each_calculator_session_uses_its_own_csv(tmp_path):
    first_session = make_calculator(tmp_path)
    first_session.calculate("+", 1, 2)
    first_session.close()

    second_session = make_calculator(tmp_path)
    second_session.close()

    assert first_session.session_history_file != second_session.session_history_file
    assert first_session.session_history_file.exists()
    assert second_session.session_history_file.exists()
    assert "1 + 2 = 3" in first_session.history_text()
    assert second_session.history_text() == "No calculations yet."
    assert len(list(tmp_path.glob("history_*.csv"))) == 2


def test_calculator_load_missing_file_keeps_empty_history(tmp_path):
    calculator = make_calculator(tmp_path, auto_save=False)

    calculator.load()

    assert calculator.history_text() == "No calculations yet."
    assert calculator.undo() is True


def test_calculator_loads_selected_entry_from_previous_session(tmp_path):
    archive_file = tmp_path / "history_previous.csv"
    pd.DataFrame(
        [[4, "*", 5, 20], [8, "+", 1, 9]],
        columns=["first_operand", "operator", "second_operand", "result"],
    ).to_csv(archive_file, index=False)
    calculator = make_calculator(tmp_path, auto_save=False)

    loaded = calculator.load_entry(2)

    assert str(loaded) == "8.0 + 1.0 = 9.0"
    assert calculator.history_entries()[-1] == {
        "first_operand": 8.0,
        "operator": "+",
        "second_operand": 1.0,
        "result": 9.0,
        "timestamp": calculator.history_entries()[-1]["timestamp"],
    }


@pytest.mark.parametrize("entry_number", [0, 2, "1"])
def test_calculator_rejects_invalid_saved_entry_number(tmp_path, entry_number):
    pd.DataFrame(
        [[4, "*", 5, 20]],
        columns=["first_operand", "operator", "second_operand", "result"],
    ).to_csv(tmp_path / "history_previous.csv", index=False)
    calculator = make_calculator(tmp_path, auto_save=False)

    with pytest.raises(ValueError, match="Choose a listed saved-entry number"):
        calculator.load_entry(entry_number)


def test_calculator_configuration_failure_is_propagated(monkeypatch):
    monkeypatch.setenv("CALCULATOR_AUTO_SAVE", "invalid")

    with pytest.raises(ValueError, match="CALCULATOR_AUTO_SAVE"):
        Calculator()
