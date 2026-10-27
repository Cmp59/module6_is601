from unittest.mock import patch
import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest

from app.calculator import Calculator
from app.exceptions import ConfigurationError, HistoryError
from app.calculator_repl import calculator


@pytest.mark.parametrize(
    "first_number, operator, second_number, expected_result",
    [
        ("2", "add", "3", "Result: 5.0"),
        ("5", "subtract", "3", "Result: 2.0"),
        ("2", "multiply", "3", "Result: 6.0"),
        ("6", "divide", "3", "Result: 2.0"),
        ("7", "modulus", "3", "Result: 1.0"),
        ("-7", "int_divide", "3", "Result: -2"),
        ("25", "percent", "200", "Result: 12.5"),
        ("3", "abs_diff", "8", "Result: 5.0"),
        ("2", "power", "3", "Result: 8.0"),
        ("27", "root", "3", "Result: 3.0"),
    ],
)
def test_calculator_performs_operations(
    first_number, operator, second_number, expected_result, capsys
):
    with patch(
        "builtins.input",
        side_effect=[first_number, operator, second_number, "q"],
    ):
        calculator()

    assert expected_result in capsys.readouterr().out


@pytest.mark.parametrize("quit_command", ["q", "exit"])
def test_calculator_quits_at_first_number(quit_command, capsys):
    with patch("builtins.input", return_value=quit_command):
        calculator()

    output = capsys.readouterr().out
    assert "Enter exit or q at any prompt to quit" in output
    assert "Commands: help, history, clear, undo, redo, save, load, exit" in output


@pytest.mark.parametrize("quit_command", ["q", "exit"])
def test_calculator_quits_at_operator(quit_command):
    with patch("builtins.input", side_effect=["2", quit_command]):
        calculator()


@pytest.mark.parametrize("quit_command", ["q", "exit"])
def test_calculator_quits_at_second_number(quit_command):
    with patch("builtins.input", side_effect=["2", "add", quit_command]):
        calculator()


def test_calculator_rejects_unsupported_operation(capsys):
    with patch("builtins.input", side_effect=["2", "+", "q"]):
        calculator()

    assert "Please choose add, subtract, multiply, divide" in capsys.readouterr().out


def test_calculator_rejects_non_numeric_first_number(capsys):
    with patch("builtins.input", side_effect=["abc", "add", "2", "q"]):
        calculator()

    assert "Invalid number: abc" in capsys.readouterr().out


def test_calculator_rejects_non_numeric_second_number(capsys):
    with patch("builtins.input", side_effect=["2", "add", "abc", "q"]):
        calculator()

    assert "Invalid number: abc" in capsys.readouterr().out


def test_calculator_handles_division_by_zero(capsys):
    with patch("builtins.input", side_effect=["2", "divide", "0", "q"]):
        calculator()

    assert "You cannot divide by zero." in capsys.readouterr().out


def test_calculator_displays_empty_history(capsys):
    with patch("builtins.input", side_effect=["history", "q"]):
        calculator()

    assert "No calculations yet." in capsys.readouterr().out


def test_calculator_help_command(capsys):
    with patch("builtins.input", side_effect=["help", "exit"]):
        calculator()

    output = capsys.readouterr().out
    assert "Commands: help, history, clear, undo, redo, save, load, exit" in output
    assert "Operations: add, subtract, multiply, divide, power, root" in output


def test_calculator_handles_help_at_operator_prompt(capsys):
    with patch("builtins.input", side_effect=["2", "help", "exit"]):
        calculator()

    assert "Commands: help, history, clear, undo, redo, save, load, exit" in capsys.readouterr().out


def test_calculator_handles_history_at_second_number_prompt(capsys):
    with patch("builtins.input", side_effect=["2", "add", "history", "exit"]):
        calculator()

    assert "No calculations yet." in capsys.readouterr().out


def test_calculator_displays_completed_history(capsys):
    with patch("builtins.input", side_effect=["2", "add", "3", "history", "q"]):
        calculator()

    assert "1. 2.0 add 3.0 = 5.0" in capsys.readouterr().out


def test_failed_calculation_is_not_added_to_history(capsys):
    with patch(
        "builtins.input",
        side_effect=["2", "divide", "0", "history", "q"],
    ):
        calculator()

    output = capsys.readouterr().out
    assert "You cannot divide by zero." in output
    assert "No calculations yet." in output


def test_calculator_reports_invalid_root(capsys):
    with patch("builtins.input", side_effect=["-9", "root", "2", "exit"]):
        calculator()

    assert "negative number requires an odd integer root degree" in capsys.readouterr().out


def test_calculator_module_starts_repl(monkeypatch):
    monkeypatch.delitem(sys.modules, "app.calculator_repl", raising=False)
    with patch("builtins.input", return_value="q"):
        runpy.run_module("app.calculator_repl", run_name="__main__")


def test_repl_saves_session_csv_when_exiting(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("CALCULATOR_HISTORY_FILE", str(tmp_path / "history.csv"))
    with patch("builtins.input", side_effect=["2", "add", "3", "exit"]):
        calculator()

    output = capsys.readouterr().out
    assert "Result: 5.0" in output
    assert "Session history saved to:" in output
    csv_files = list(tmp_path.glob("history_*.csv"))
    assert csv_files
    text_file = csv_files[-1].with_suffix(".txt")
    assert f"Session history saved to: {csv_files[-1].resolve()}" in output
    assert f"Session log saved to: {text_file.resolve()}" in output
    assert text_file.exists()
    session_log = text_file.read_text(encoding="utf-8")
    assert "Session started:" in session_log
    assert "Input (First number): 2" in session_log
    assert "Input (Operation): add" in session_log
    assert "Input (Second number): 3" in session_log
    assert "Calculation: 2.0 add 3.0 = 5.0" in session_log
    assert "Session ended:" in session_log
    saved = pd.read_csv(csv_files[-1])
    assert list(saved.columns) == [
        "first_operand",
        "operator",
        "second_operand",
        "result",
    ]
    assert saved.iloc[-1].to_dict() == {
        "first_operand": 2.0,
        "operator": "add",
        "second_operand": 3.0,
        "result": 5.0,
    }


@pytest.mark.parametrize("prompt_values", [["clear", "exit"], ["2", "clear", "exit"]])
def test_calculator_clear_command(prompt_values, capsys):
    with patch("builtins.input", side_effect=prompt_values):
        calculator()

    assert "Calculator reset: cleared current-session history" in capsys.readouterr().out


@pytest.mark.parametrize(
    "command, expected",
    [
        ("undo", "Undo: no calculation to remove."),
        ("redo", "Redo: no undone calculation to restore."),
        ("save", "Saved 0 calculation(s) to"),
        ("load", "Load: no calculations found in previous session CSV files."),
    ],
)
def test_calculator_state_commands(command, expected, capsys):
    with patch("builtins.input", side_effect=[command, "exit"]):
        calculator()

    assert expected in capsys.readouterr().out


@pytest.mark.parametrize("exception_type", [EOFError, KeyboardInterrupt])
@pytest.mark.parametrize(
    "input_before_interrupt",
    [[], ["2"], ["2", "add"]],
)
def test_calculator_exits_gracefully_on_input_interruption(
    exception_type, input_before_interrupt, capsys
):
    with patch(
        "builtins.input",
        side_effect=[*input_before_interrupt, exception_type()],
    ):
        calculator()

    assert "Input interrupted. Exiting calculator." in capsys.readouterr().out


def test_calculator_reports_configuration_error(monkeypatch, capsys):
    monkeypatch.setenv("CALCULATOR_AUTO_SAVE", "invalid")

    calculator()

    assert "Calculator configuration/history error" in capsys.readouterr().out


def test_calculator_reports_save_errors(monkeypatch, capsys):
    monkeypatch.setattr(
        Calculator,
        "save",
        lambda self: (_ for _ in ()).throw(ConfigurationError("save failed")),
    )
    with patch("builtins.input", side_effect=["save", "exit"]):
        calculator()

    assert "Save failed: save failed" in capsys.readouterr().out


def test_calculator_reports_load_errors(monkeypatch, capsys):
    monkeypatch.setattr(
        Calculator,
        "saved_entries",
        lambda self: (_ for _ in ()).throw(ConfigurationError("load failed")),
    )
    with patch("builtins.input", side_effect=["load", "exit"]):
        calculator()

    assert "Load failed: load failed" in capsys.readouterr().out


def test_calculator_reports_session_save_error(monkeypatch, capsys):
    monkeypatch.setattr(
        Calculator,
        "close",
        lambda self: (_ for _ in ()).throw(HistoryError("session save failed")),
    )
    with patch("builtins.input", return_value="exit"):
        calculator()

    assert "Error saving session history: session save failed" in capsys.readouterr().out


def test_undo_and_redo_report_the_entry(capsys):
    with patch(
        "builtins.input",
        side_effect=["2", "add", "3", "undo", "redo", "exit"],
    ):
        calculator()

    output = capsys.readouterr().out
    assert "Undo: removed 2.0 add 3.0 = 5.0 from history." in output
    assert "Redo: restored 2.0 add 3.0 = 5.0 to history." in output


def test_load_lists_and_imports_selected_previous_session_entry(
    capsys, monkeypatch, tmp_path
):
    monkeypatch.setenv("CALCULATOR_HISTORY_FILE", str(tmp_path / "history.csv"))
    pd.DataFrame(
        [[7, "^", 2, 49], [9, "root", 2, 3]],
        columns=["first_operand", "operator", "second_operand", "result"],
    ).to_csv(tmp_path / "history_previous.csv", index=False)
    with patch("builtins.input", side_effect=["load", "2", "history", "exit"]):
        calculator()

    output = capsys.readouterr().out
    assert "[1] 7 ^ 2 = 49" in output
    assert "[2] 9 root 2 = 3" in output
    assert "Loaded calculation into this session: 9.0 root 2.0 = 3.0." in output
    assert "1. 9.0 root 2.0 = 3.0" in output


@pytest.mark.parametrize("selection", ["abc", "0", "8"])
def test_load_reports_invalid_selection(capsys, monkeypatch, tmp_path, selection):
    monkeypatch.setenv("CALCULATOR_HISTORY_FILE", str(tmp_path / "history.csv"))
    pd.DataFrame(
        [[2, "+", 3, 5]],
        columns=["first_operand", "operator", "second_operand", "result"],
    ).to_csv(tmp_path / "history_previous.csv", index=False)
    with patch("builtins.input", side_effect=["load", selection, "exit"]):
        calculator()

    assert "Load failed: Choose a listed saved-entry number." in capsys.readouterr().out


def test_load_can_be_cancelled(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("CALCULATOR_HISTORY_FILE", str(tmp_path / "history.csv"))
    pd.DataFrame(
        [[2, "+", 3, 5]],
        columns=["first_operand", "operator", "second_operand", "result"],
    ).to_csv(tmp_path / "history_previous.csv", index=False)
    with patch("builtins.input", side_effect=["load", "cancel", "history", "exit"]):
        calculator()

    output = capsys.readouterr().out
    assert "Load cancelled; current history is unchanged." in output
    assert "No calculations yet." in output


@pytest.mark.parametrize(
    "command, method_name, expected_message",
    [
        ("clear", "clear", "Clear failed: history unavailable"),
        ("undo", "undo", "Undo failed: history unavailable"),
        ("redo", "redo", "Redo failed: history unavailable"),
    ],
)
def test_state_commands_report_errors(
    command, method_name, expected_message, monkeypatch, capsys
):
    monkeypatch.setattr(
        Calculator,
        method_name,
        lambda self: (_ for _ in ()).throw(HistoryError("history unavailable")),
    )
    with patch("builtins.input", side_effect=[command, "exit"]):
        calculator()

    assert expected_message in capsys.readouterr().out


def test_load_selection_can_be_interrupted(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("CALCULATOR_HISTORY_FILE", str(tmp_path / "history.csv"))
    pd.DataFrame(
        [[2, "+", 3, 5]],
        columns=["first_operand", "operator", "second_operand", "result"],
    ).to_csv(tmp_path / "history_previous.csv", index=False)
    with patch("builtins.input", side_effect=["load", KeyboardInterrupt()]):
        calculator()

    output = capsys.readouterr().out
    assert "Input interrupted. Exiting calculator." in output
    assert "Session history saved to:" in output