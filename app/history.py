"""Observer-based, pandas-backed calculation history with CSV persistence."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple

import pandas as pd

from .calculation import Calculation
from .exceptions import HistoryError

HISTORY_COLUMNS = [
    "first_operand",
    "operator",
    "second_operand",
    "result",
    "timestamp",
]
LEGACY_HISTORY_COLUMNS = HISTORY_COLUMNS[:-1]


class CalculationObserver(ABC):
    """Observer interface for completed calculations."""

    @abstractmethod
    def update(self, calculation: Calculation) -> None:
        """React to a completed calculation event."""


class CalculationSubject:
    """Publish completed-calculation events to attached observers."""

    def __init__(self):
        self._observers = []

    def attach(self, observer: CalculationObserver) -> None:
        """Subscribe an observer once."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: CalculationObserver) -> None:
        """Unsubscribe an observer if currently attached."""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, calculation: Calculation) -> None:
        """Notify a stable snapshot of observers about a calculation."""
        for observer in tuple(self._observers):
            observer.update(calculation)


class CalculationHistory(CalculationObserver):
    """Observe calculation events and persist them in a pandas DataFrame."""

    def __init__(
        self,
        history_file: Path,
        auto_save: bool = True,
        max_history_size: int = 10000,
        encoding: str = "utf-8",
    ):
        self.history_file = Path(history_file)
        self.auto_save = auto_save
        self.max_history_size = max_history_size
        self.encoding = encoding
        self._data = pd.DataFrame(columns=HISTORY_COLUMNS)
        self._saved_data = pd.DataFrame(columns=HISTORY_COLUMNS + ["_session_file"])

    @property
    def dataframe(self) -> pd.DataFrame:
        """Return a defensive copy of the history table."""
        return self._data.copy(deep=True)

    def update(self, calculation: Calculation) -> None:
        """Append a calculation event and auto-save when configured."""
        if calculation.result is None:
            raise HistoryError("Cannot record a calculation before it is performed.")
        row = {
            "first_operand": calculation.first_number,
            "operator": calculation.operator_symbol,
            "second_operand": calculation.second_number,
            "result": calculation.result,
            "timestamp": calculation.timestamp,
        }
        self._data.loc[len(self._data)] = row
        self._trim_history()
        if self.auto_save:
            self.save()

    def add(self, calculation: Calculation) -> None:
        """Compatibility method that records through the observer interface."""
        self.update(calculation)

    def get_all(self) -> Tuple[dict, ...]:
        """Return history rows as immutable snapshots of dictionaries."""
        return tuple(self._data.to_dict(orient="records"))

    def load_saved_sessions(
        self, filename_prefix: Path, exclude_history_file: Path
    ) -> None:
        """Load earlier session CSVs into a separate archive DataFrame."""
        session_frames = []
        pattern = f"{filename_prefix.stem}_*.csv"
        try:
            session_files = sorted(filename_prefix.parent.glob(pattern))
            for session_file in session_files:
                if session_file == Path(exclude_history_file):
                    continue
                saved_data = pd.read_csv(session_file, encoding=self.encoding)
                if list(saved_data.columns) == LEGACY_HISTORY_COLUMNS:
                    saved_data["timestamp"] = ""
                elif list(saved_data.columns) != HISTORY_COLUMNS:
                    raise HistoryError(
                        f"Saved history has an invalid column layout: {session_file}"
                    )
                saved_data = saved_data[HISTORY_COLUMNS]
                saved_data["_session_file"] = session_file
                session_frames.append(saved_data)
        except (
            OSError,
            UnicodeError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
        ) as error:
            raise HistoryError(f"Could not read saved history: {error}") from error
        if session_frames:
            self._saved_data = pd.concat(session_frames, ignore_index=True)
        else:
            self._saved_data = pd.DataFrame(
                columns=HISTORY_COLUMNS + ["_session_file"]
            )

    def get_saved_entries(self) -> Tuple[dict, ...]:
        """Return the archive entries loaded when this calculator started."""
        return tuple(self._saved_data.to_dict(orient="records"))

    def format_entries(self) -> str:
        """Format history entries for display in the REPL."""
        if self._data.empty:
            return "No calculations yet."

        lines = []
        for index, row in self._data.iterrows():
            lines.append(
                f"{index + 1}. {row['first_operand']} {row['operator']} "
                f"{row['second_operand']} = {row['result']}"
            )
        return "\n".join(lines)

    def clear(self) -> None:
        """Remove all in-memory history and update persistent history."""
        self._data = pd.DataFrame(columns=HISTORY_COLUMNS)
        if self.auto_save:
            self.save()

    def save(self) -> None:
        """Persist the current history DataFrame to CSV."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self._data.to_csv(
                self.history_file, index=False, encoding=self.encoding
            )
        except (OSError, UnicodeError) as error:
            raise HistoryError(f"Could not save history: {error}") from error

    def load(self) -> None:
        """Load existing CSV history, rejecting malformed columns."""
        try:
            loaded = pd.read_csv(self.history_file, encoding=self.encoding)
        except FileNotFoundError:
            self._data = pd.DataFrame(columns=HISTORY_COLUMNS)
            return
        except (
            OSError,
            UnicodeError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
        ) as error:
            raise HistoryError(f"Could not load history: {error}") from error

        if list(loaded.columns) == LEGACY_HISTORY_COLUMNS:
            loaded["timestamp"] = ""
        elif list(loaded.columns) != HISTORY_COLUMNS:
            raise HistoryError("History CSV has an invalid column layout.")
        self._data = loaded[HISTORY_COLUMNS].tail(self.max_history_size).reset_index(drop=True)

    def snapshot_rows(self):
        """Return raw row values for memento snapshots."""
        return tuple(self._data.itertuples(index=False, name=None))

    def restore_rows(self, rows) -> None:
        """Restore history from an immutable snapshot of rows."""
        normalized_rows = [
            tuple(row) if len(row) == len(HISTORY_COLUMNS) else (*row, "")
            for row in rows
        ]
        self._data = pd.DataFrame(
            normalized_rows, columns=HISTORY_COLUMNS
        ).tail(self.max_history_size).reset_index(drop=True)
        if self.auto_save:
            self.save()

    def _trim_history(self) -> None:
        self._data = self._data.tail(self.max_history_size).reset_index(drop=True)