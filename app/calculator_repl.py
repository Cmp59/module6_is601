"""Interactive command-line interface for the Calculator facade."""

from .calculator import Calculator
from .exceptions import CalculatorError
from .input_validators import normalize_command, parse_number

HELP_TEXT = (
    "Commands: help, history, clear, undo, redo, save, load, exit (q also exits).\n"
    "Operations: add, subtract, multiply, divide, power, root, modulus, "
    "int_divide, percent, abs_diff.\n"
    "For root, enter the radicand first and the root degree second.\n"
    "clear deletes this session's history and resets undo/redo.\n"
    "undo removes the last entry; redo restores the last undone entry.\n"
    "save writes this session; load lists earlier sessions and imports a selected entry."
)

OPERATION_COMMANDS = frozenset(
    {
        "add",
        "subtract",
        "multiply",
        "divide",
        "power",
        "root",
        "modulus",
        "int_divide",
        "percent",
        "abs_diff",
    }
)


def _read_input(prompt):
    """Read one prompt, returning None for EOF or an interrupt."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("Input interrupted. Exiting calculator.")
        return None


def _handle_command(user_input, calculator):
    """Handle a REPL command, returning its control-flow action."""
    command = normalize_command(user_input)
    if command in ("q", "exit"):
        print("Exiting calculator.")
        return "exit"
    if command == "help":
        print("Available commands and operations:")
        print(HELP_TEXT)
        return "handled"
    if command == "history":
        print("Current session history:")
        print(calculator.history_text())
        return "handled"
    if command == "clear":
        try:
            removed_count = calculator.clear()
        except CalculatorError as error:
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
            print(f"Save failed: {error}")
        else:
            print(f"Saved {entry_count} calculation(s) to {session_file}.")
        return "handled"
    if command == "load":
        try:
            entries = calculator.saved_entries()
        except CalculatorError as error:
            print(f"Load failed: {error}")
            return "handled"
        if not entries:
            print("Load: no calculations found in previous session CSV files.")
            return "handled"

        print("Saved calculations from previous sessions:")
        for entry_number, entry in enumerate(entries, start=1):
            print(
                f"[{entry_number}] {entry['first_operand']} {entry['operator']} "
                f"{entry['second_operand']} = {entry['result']} "
                f"({entry['_session_file'].name})"
            )
        selection = _read_input("Enter an entry number to load, or 'cancel': ")
        if selection is None:
            return "exit"
        if normalize_command(selection) == "cancel":
            print("Load cancelled; current history is unchanged.")
            return "handled"
        try:
            entry_number = int(selection)
        except ValueError:
            print("Load failed: Choose a listed saved-entry number.")
            return "handled"
        try:
            calculation = calculator.load_entry(entry_number)
        except (ValueError, CalculatorError) as error:
            print(f"Load failed: {error}")
        else:
            print(f"Loaded calculation into this session: {calculation}.")
        return "handled"
    return None


def calculator():
    """Run the calculator until the user chooses to quit."""
    try:
        calculator_app = Calculator()
    except CalculatorError as error:
        print(f"Calculator configuration/history error: {error}")
        return
    print(
        "Calculator: enter help for commands. Enter exit or q at any prompt to quit."
    )
    print("Commands: help, history, clear, undo, redo, save, load, exit (q also exits).")

    while True:
        first_input = _read_input("First number: ")
        if first_input is None:
            break
        command_action = _handle_command(first_input, calculator_app)
        if command_action == "exit":
            break
        if command_action == "handled":
            continue

        operator = _read_input("Operation: ")
        if operator is None:
            break
        operator = normalize_command(operator)
        command_action = _handle_command(operator, calculator_app)
        if command_action == "exit":
            break
        if command_action == "handled":
            continue
        if operator not in OPERATION_COMMANDS or not calculator_app.supports(operator):
            print(
                "Please choose add, subtract, multiply, divide, power, root, "
                "modulus, int_divide, percent, or abs_diff."
            )
            continue

        second_input = _read_input("Second number: ")
        if second_input is None:
            break
        command_action = _handle_command(second_input, calculator_app)
        if command_action == "exit":
            break
        if command_action == "handled":
            continue

        try:
            first_number = parse_number(first_input)
            second_number = parse_number(second_input)
            result = calculator_app.calculate(
                operator, first_number, second_number
            )
        except CalculatorError as error:
            print(f"Error: {error}")
            continue

        print(f"Result: {result}")

    try:
        session_file = calculator_app.close()
    except CalculatorError as error:
        print(f"Error saving session history: {error}")
    else:
        print(f"Session history saved to: {session_file}")


if __name__ == "__main__":
    calculator()