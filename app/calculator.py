"""Facade coordinating calculator operations, history, and state."""

from .calculator_config import CalculatorConfig
from .calculator_memento import CalculatorMemento
from .calculation import CalculationFactory
from .exceptions import InvalidInputError
from .history import CalculationHistory, CalculationSubject
from .logger import Logger, LoggingObserver


class Calculator:
    """Provide a simple interface to calculator subsystems."""

    def __init__(self, config=None):
        self.config = config or CalculatorConfig.load()
        self.session_history_file = self.config.new_session_history_file()
        self.history = CalculationHistory(
            self.session_history_file,
            auto_save=self.config.auto_save,
            max_history_size=self.config.max_history_size,
            encoding=self.config.default_encoding,
        )
        self.logger = Logger(self.config.log_file, self.config.default_encoding)
        self._events = CalculationSubject()
        self._events.attach(self.history)
        self._events.attach(LoggingObserver(self.logger))
        self._undo_stack = []
        self._redo_stack = []
        self.history.load()
        self.history.save()
        self.history.load_saved_sessions(
            self.config.history_file, self.session_history_file
        )
        self.logger.info("Calculator session started")

    def supports(self, operator):
        """Return whether an operation symbol is supported."""
        return CalculationFactory.supports(operator)

    def calculate(self, operator, first_number, second_number):
        """Create, perform, publish, and return a calculation result."""
        self._validate_input(first_number)
        self._validate_input(second_number)
        calculation = CalculationFactory.create(
            operator, first_number, second_number
        )
        result = round(calculation.perform(), self.config.precision)
        calculation.result = result
        self._undo_stack.append(self._create_memento())
        self._redo_stack.clear()
        self._events.notify(calculation)
        return result

    def history_text(self):
        """Return formatted history for the command-line interface."""
        return self.history.format_entries()

    def history_entries(self):
        """Return current-session calculation records."""
        return self.history.get_all()

    def clear(self):
        """Clear history and reset the undo/redo state completely."""
        removed_count = len(self.history.get_all())
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.history.clear()
        return removed_count

    def undo(self):
        """Restore the previous state, if one is available."""
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._create_memento())
        self._restore(self._undo_stack.pop())
        return True

    def redo(self):
        """Reapply a state previously removed by undo."""
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._create_memento())
        self._restore(self._redo_stack.pop())
        return True

    def save(self):
        """Persist current history and return its path and entry count."""
        self.history.save()
        return self.session_history_file, len(self.history.get_all())

    def saved_entries(self):
        """Return calculations loaded from previous sessions at startup."""
        return self.history.get_saved_entries()

    def load_entry(self, entry_number):
        """Copy a selected archived calculation into the current session."""
        entries = self.saved_entries()
        if not isinstance(entry_number, int) or not 1 <= entry_number <= len(entries):
            raise InvalidInputError("Choose a listed saved-entry number.")

        entry = entries[entry_number - 1]
        calculation = CalculationFactory.create(
            entry["operator"],
            float(entry["first_operand"]),
            float(entry["second_operand"]),
        )
        calculation.result = round(calculation.perform(), self.config.precision)
        self._undo_stack.append(self._create_memento())
        self._redo_stack.clear()
        self._events.notify(calculation)
        return calculation

    def close(self):
        """Save this session's CSV and return its path."""
        self.history.save()
        self.logger.info("Calculator session ended")
        self.logger.close()
        return self.session_history_file

    def load(self):
        """Load history as an undoable state change."""
        previous_state = self._create_memento()
        self.history.load()
        self._undo_stack.append(previous_state)
        self._redo_stack.clear()

    def _create_memento(self):
        return CalculatorMemento.from_rows(self.history.snapshot_rows())

    def _restore(self, memento):
        self.history.restore_rows(memento.rows)

    def _validate_input(self, value):
        try:
            valid_number = abs(value) <= self.config.max_input_value
        except TypeError as error:
            raise InvalidInputError("Inputs must be numeric values.") from error
        if not valid_number:
            raise InvalidInputError(
                f"Input value exceeds the maximum of {self.config.max_input_value}."
            )