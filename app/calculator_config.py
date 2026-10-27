"""Load and validate calculator configuration from environment variables."""

import codecs
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from dotenv import dotenv_values

from .exceptions import ConfigurationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CalculatorConfig:
    """Validated settings used by the calculator application."""

    history_file: Path
    auto_save: bool
    history_dir: Optional[Path] = None
    log_dir: Optional[Path] = None
    log_file: Optional[Path] = None
    max_history_size: int = 10000
    precision: int = 10
    max_input_value: float = 1_000_000_000
    default_encoding: str = "utf-8"

    def __post_init__(self):
        object.__setattr__(self, "history_file", Path(self.history_file))
        if self.history_dir is None:
            object.__setattr__(self, "history_dir", self.history_file.parent)
        if self.log_dir is None:
            object.__setattr__(self, "log_dir", self.history_file.parent / "logs")
        if self.log_file is None:
            object.__setattr__(self, "log_file", self.log_dir / "calculator.log")

    def new_session_history_file(self) -> Path:
        """Return a unique CSV path for a new REPL session."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{self.history_file.stem}_{timestamp}_{uuid4().hex[:8]}.csv"
        return self.history_dir / filename

    @classmethod
    def load(cls, env_file: Optional[Path] = None):
        """Load dotenv values and validate supported settings."""
        dotenv_file = Path(env_file) if env_file is not None else PROJECT_ROOT / ".env"
        dotenv_config = dotenv_values(dotenv_file)

        def setting(name: str, default: str) -> str:
            return os.getenv(name, dotenv_config.get(name) or default).strip()

        history_file_value = setting("CALCULATOR_HISTORY_FILE", "history.csv")
        history_dir_value = setting("CALCULATOR_HISTORY_DIR", "data/history")
        log_dir_value = setting("CALCULATOR_LOG_DIR", "data/logs")
        log_file_value = setting("CALCULATOR_LOG_FILE", "calculator.log")
        auto_save_value = setting("CALCULATOR_AUTO_SAVE", "true").lower()

        if not history_file_value:
            raise ConfigurationError("CALCULATOR_HISTORY_FILE cannot be empty.")
        if not history_dir_value:
            raise ConfigurationError("CALCULATOR_HISTORY_DIR cannot be empty.")
        if not log_dir_value:
            raise ConfigurationError("CALCULATOR_LOG_DIR cannot be empty.")
        if not log_file_value:
            raise ConfigurationError("CALCULATOR_LOG_FILE cannot be empty.")
        if auto_save_value not in {"true", "false"}:
            raise ConfigurationError(
                "CALCULATOR_AUTO_SAVE must be 'true' or 'false'."
            )

        try:
            history_dir = cls._resolve_directory(history_dir_value)
            log_dir = cls._resolve_directory(log_dir_value)
            history_file_path = Path(history_file_value).expanduser()
            if history_file_path.is_absolute():
                history_dir = history_file_path.parent
                history_file = history_file_path
            elif history_file_path.parent != Path("."):
                if "CALCULATOR_HISTORY_DIR" not in os.environ and not dotenv_config.get(
                    "CALCULATOR_HISTORY_DIR"
                ):
                    history_file = PROJECT_ROOT / history_file_path
                    history_dir = history_file.parent
                else:
                    history_file = history_dir / history_file_path.name
            else:
                history_file = history_dir / history_file_path.name

            if not history_file.name or history_file.name in {".", ".."}:
                raise ConfigurationError(
                    "CALCULATOR_HISTORY_FILE must include a filename prefix."
                )
            if history_file.exists() and history_file.is_dir():
                raise ConfigurationError(
                    "CALCULATOR_HISTORY_FILE must be a file path prefix, not a directory."
                )
            if history_file.parent.exists() and not history_file.parent.is_dir():
                raise ConfigurationError(
                    "The parent of CALCULATOR_HISTORY_FILE must be a directory."
                )
            for directory_name, directory in (
                ("CALCULATOR_HISTORY_DIR", history_dir),
                ("CALCULATOR_LOG_DIR", log_dir),
            ):
                if directory.exists() and not directory.is_dir():
                    raise ConfigurationError(f"{directory_name} must be a directory.")
            log_file_path = Path(log_file_value).expanduser()
            log_file = (
                log_file_path
                if log_file_path.is_absolute()
                else log_dir / log_file_path
            )
            if not history_dir.name or not log_dir.name or not log_file.name:
                raise ConfigurationError("History and log directories must be valid paths.")
            if log_file.exists() and log_file.is_dir():
                raise ConfigurationError("CALCULATOR_LOG_FILE must be a file path.")
            if log_file.parent.exists() and not log_file.parent.is_dir():
                raise ConfigurationError(
                    "The parent of CALCULATOR_LOG_FILE must be a directory."
                )
        except OSError as error:
            raise ConfigurationError(
                f"Invalid configuration path: {error}"
            ) from error

        max_history_size = cls._positive_integer(
            "CALCULATOR_MAX_HISTORY_SIZE",
            setting("CALCULATOR_MAX_HISTORY_SIZE", "10000"),
        )
        precision = cls._nonnegative_integer(
            "CALCULATOR_PRECISION", setting("CALCULATOR_PRECISION", "10")
        )
        max_input_value = cls._positive_float(
            "CALCULATOR_MAX_INPUT_VALUE",
            setting("CALCULATOR_MAX_INPUT_VALUE", "1000000000"),
        )
        default_encoding = setting("CALCULATOR_DEFAULT_ENCODING", "utf-8")
        if not default_encoding:
            raise ConfigurationError("CALCULATOR_DEFAULT_ENCODING cannot be empty.")
        try:
            codecs.lookup(default_encoding)
        except LookupError as error:
            raise ConfigurationError(
                f"Unknown CALCULATOR_DEFAULT_ENCODING: {default_encoding}"
            ) from error

        return cls(
            history_file=history_file,
            auto_save=auto_save_value == "true",
            history_dir=history_dir,
            log_dir=log_dir,
            log_file=log_file,
            max_history_size=max_history_size,
            precision=precision,
            max_input_value=max_input_value,
            default_encoding=default_encoding,
        )

    @staticmethod
    def _resolve_directory(value: str) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else PROJECT_ROOT / path

    @staticmethod
    def _positive_integer(name: str, value: str) -> int:
        try:
            number = int(value)
        except ValueError as error:
            raise ConfigurationError(f"{name} must be a positive integer.") from error
        if number < 1:
            raise ConfigurationError(f"{name} must be a positive integer.")
        return number
    @staticmethod
    def _nonnegative_integer(name: str, value: str) -> int:
        try:
            number = int(value)
        except ValueError as error:
            raise ConfigurationError(f"{name} must be a nonnegative integer.") from error
        if number < 0:
            raise ConfigurationError(f"{name} must be a nonnegative integer.")
        return number

    @staticmethod
    def _positive_float(name: str, value: str) -> float:
        try:
            number = float(value)
        except ValueError as error:
            raise ConfigurationError(f"{name} must be a positive number.") from error
        if not math.isfinite(number) or number <= 0:
            raise ConfigurationError(f"{name} must be a positive finite number.")
        return number

