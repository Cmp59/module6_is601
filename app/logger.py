"""Write a plain-text record of one calculator session."""

import logging
from datetime import datetime, timezone
from pathlib import Path


class Logger:
    """Configure and expose the calculator's application log."""

    def __init__(self, log_file: Path, encoding: str = "utf-8"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger(f"calculator.{self.log_file.resolve()}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        if not self._logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding=encoding)
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            )
            self._logger.addHandler(handler)

    def info(self, message: str, *args) -> None:
        self._logger.info(message, *args)

    def warning(self, message: str, *args) -> None:
        self._logger.warning(message, *args)

    def error(self, message: str, *args) -> None:
        self._logger.error(message, *args)

    def close(self) -> None:
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
            handler.close()


class LoggingObserver:
    """Log completed calculations through the configured application logger."""

    def __init__(self, logger: Logger):
        self.logger = logger

    def update(self, calculation) -> None:
        self.logger.info(
            "Calculation: %s %s %s = %s",
            calculation.first_number,
            calculation.operator_symbol,
            calculation.second_number,
            calculation.result,
        )


class SessionLogger:
    """Collect session events and write them beside the session CSV."""

    def __init__(self, session_file: Path, encoding: str = "utf-8"):
        self.log_file = Path(session_file).with_suffix(".txt")
        self.encoding = encoding
        self.started_at = datetime.now(timezone.utc)
        self._events = []

    def record_input(self, prompt: str, value: str) -> None:
        """Record a value entered at a REPL prompt."""
        self._events.append(f"Input ({prompt}): {value}")

    def record_calculation(
        self, operator: str, first_number: float, second_number: float, result: float
    ) -> None:
        """Record a completed calculation."""
        self._events.append(
            f"Calculation: {first_number} {operator} {second_number} = {result}"
        )

    def close(self) -> Path:
        """Write the session record and return its path."""
        ended_at = datetime.now(timezone.utc)
        lines = [
            f"Session started: {self.started_at.isoformat()}",
            *self._events,
            f"Session ended: {ended_at.isoformat()}",
        ]
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.write_text("\n".join(lines) + "\n", encoding=self.encoding)
        return self.log_file