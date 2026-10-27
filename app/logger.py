"""Write a plain-text record of one calculator session."""

from datetime import datetime, timezone
from pathlib import Path


class SessionLogger:
    """Collect session events and write them beside the session CSV."""

    def __init__(self, session_file: Path):
        self.log_file = Path(session_file).with_suffix(".txt")
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
        self.log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.log_file