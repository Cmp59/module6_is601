"""Interactive command-line interface for the Calculator facade."""

from .calculator import Calculator
from .exceptions import CalculatorError
from .help_menu import render_help_text
from .input_validators import normalize_command, parse_number
from .logger import SessionLogger
from .operations import OperationFactory


def _record_issue(calculator_app, session_logger, message, *, error=False):
    """Record a user-facing issue in the session journal and app log."""
    if session_logger is not None:
        recorder = session_logger.record_error if error else session_logger.record_warning
        recorder(message)
    if calculator_app is not None:
        log_method = calculator_app.logger.error if error else calculator_app.logger.warning
        log_method(message)


def _read_input(prompt, session_logger=None, calculator_app=None):
    """Read one prompt, returning None for EOF or an interrupt."""
    try:
        value = input(prompt).strip()
        if session_logger is not None:
            session_logger.record_input(prompt.rstrip(": "), value)
        return value
    except (EOFError, KeyboardInterrupt):
        _record_issue(
            calculator_app,
            session_logger,
            "Input interrupted by EOF or keyboard interrupt",
        )
        print("Input interrupted. Exiting calculator.")
        return None


def _handle_command(user_input, calculator, session_logger=None):
    """Handle a REPL command, returning its control-flow action."""
    command = normalize_command(user_input)
    if command in ("q", "exit"):
        print("Exiting calculator.")
        return "exit"
    if command == "help":
        print("Available commands and operations:")
        print(render_help_text())
        return "handled"
    if command == "history":
        print("Current session history:")
        print(calculator.history_text())
        return "handled"
    if command == "clear":
        try:
            removed_count = calculator.clear()
        except CalculatorError as error:
            _record_issue(calculator, session_logger, str(error), error=True)
            print(f"Clear failed: {error}")
        else:
            print(
                "Calculator reset: cleared current-session history and undo/redo "
                f"state ({removed_count} entr{'y' if removed_count == 1 else 'ies'} removed)."
            )
        return "handled"
    if command == "undo":
        entries = calculator.history_entries()
        try:
            undone = calculator.undo()
        except CalculatorError as error:
            _record_issue(calculator, session_logger, str(error), error=True)
            print(f"Undo failed: {error}")
        else:
            if undone:
                print(
                    f"Undo: removed {entries[-1]['first_operand']} "
                    f"{entries[-1]['operator']} {entries[-1]['second_operand']} "
                    f"= {entries[-1]['result']} from history."
                )
            else:
                print("Undo: no calculation to remove.")
        return "handled"
    if command == "redo":
        try:
            redone = calculator.redo()
        except CalculatorError as error:
            _record_issue(calculator, session_logger, str(error), error=True)
            print(f"Redo failed: {error}")
        else:
            if redone:
                entry = calculator.history_entries()[-1]
                print(
                    f"Redo: restored {entry['first_operand']} {entry['operator']} "
                    f"{entry['second_operand']} = {entry['result']} to history."
                )
            else:
                print("Redo: no undone calculation to restore.")
        return "handled"
    if command == "save":
        try:
            session_file, entry_count = calculator.save()
        except CalculatorError as error:
            _record_issue(calculator, session_logger, str(error), error=True)
            print(f"Save failed: {error}")
        else:
            print(f"Saved {entry_count} calculation(s) to {session_file}.")
        return "handled"
    if command == "load":
        try:
            sessions = calculator.saved_sessions()
        except CalculatorError as error:
            _record_issue(calculator, session_logger, str(error), error=True)
            print(f"Load failed: {error}")
            return "handled"
        if not sessions:
            print("Load: no calculations found in previous session CSV files.")
            return "handled"

        print("Saved calculation sessions:")
        for session_number, session in enumerate(sessions, start=1):
            print(
                f"[{session_number}] {session['session_file'].name} "
                f"({session['count']} calculations)"
            )
        selection = _read_input(
            "Enter a session number to load, or 'cancel': ",
            session_logger,
            calculator,
        )
        if selection is None:
            return "exit"
        if normalize_command(selection) == "cancel":
            print("Load cancelled; current history is unchanged.")
            return "handled"
        try:
            session_number = int(selection)
        except ValueError:
            message = "Choose a listed saved-session number."
            _record_issue(calculator, session_logger, message)
            print(f"Load failed: {message}")
            return "handled"
        if not 1 <= session_number <= len(sessions):
            message = "Choose a listed saved-session number."
            _record_issue(calculator, session_logger, message)
            print(f"Load failed: {message}")
            return "handled"
        try:
            session_file = sessions[session_number - 1]["session_file"]
            calculations = calculator.load_session(session_file)
        except (ValueError, CalculatorError) as error:
            _record_issue(calculator, session_logger, str(error), error=True)
            print(f"Load failed: {error}")
        else:
            for calculation in calculations:
                if session_logger is not None:
                    session_logger.record_calculation(
                        calculation.operator_symbol,
                        calculation.first_number,
                        calculation.second_number,
                        calculation.result,
                    )
            print(
                f"Loaded {len(calculations)} calculation(s) from "
                f"{session_file.name} into this session."
            )
        return "handled"
    return None


def calculator():
    """Run the calculator until the user chooses to quit."""
    try:
        calculator_app = Calculator()
    except CalculatorError as error:
        print(f"Calculator configuration/history error: {error}")
        return
    session_logger = SessionLogger(
        calculator_app.session_history_file,
        calculator_app.config.default_encoding,
    )
    print(
        "Calculator: enter help for commands. Enter exit or q at any prompt to quit."
    )
    print("Commands: help, history, clear, undo, redo, save, load, exit (q also exits).")

    while True:
        first_input = _read_input("First number: ", session_logger, calculator_app)
        if first_input is None:
            break
        command_action = _handle_command(first_input, calculator_app, session_logger)
        if command_action == "exit":
            break
        if command_action == "handled":
            continue

        operator = _read_input("Operation: ", session_logger, calculator_app)
        if operator is None:
            break
        operator = normalize_command(operator)
        command_action = _handle_command(operator, calculator_app, session_logger)
        if command_action == "exit":
            break
        if command_action == "handled":
            continue
        if operator not in OperationFactory.commands() or not calculator_app.supports(operator):
            message = (
                "Unsupported operation command: "
                f"{operator}. Enter help to see available operations."
            )
            _record_issue(calculator_app, session_logger, message)
            print("Please choose a supported word command. Enter help to list operations.")
            continue

        second_input = _read_input(
            "Second number: ", session_logger, calculator_app
        )
        if second_input is None:
            break
        command_action = _handle_command(second_input, calculator_app, session_logger)
        if command_action == "exit":
            break
        if command_action == "handled":
            continue

        try:
            first_number = parse_number(
                first_input, calculator_app.config.max_input_value
            )
            second_number = parse_number(
                second_input, calculator_app.config.max_input_value
            )
            result = calculator_app.calculate(
                operator, first_number, second_number
            )
        except CalculatorError as error:
            _record_issue(calculator_app, session_logger, str(error))
            print(f"Error: {error}")
            continue

        session_logger.record_calculation(
            operator, first_number, second_number, result
        )
        print(f"Result: {result}")

    try:
        session_file = calculator_app.close()
    except CalculatorError as error:
        _record_issue(calculator_app, session_logger, str(error), error=True)
        print(f"Error saving session history: {error}")
    else:
        print(f"Session history saved to: {session_file.resolve()}")
    try:
        log_file = session_logger.close()
    except OSError as error:
        calculator_app.logger.error("Could not save session journal: %s", error)
        print(f"Error saving session log: {error}")
    else:
        print(f"Session log saved to: {log_file.resolve()}")


if __name__ == "__main__":
    calculator()