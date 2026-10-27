from pathlib import Path

import pytest

from app.calculator_config import CalculatorConfig
from app.exceptions import ConfigurationError


def test_config_loads_defaults(monkeypatch):
    monkeypatch.delenv("CALCULATOR_HISTORY_FILE", raising=False)
    monkeypatch.delenv("CALCULATOR_HISTORY_DIR", raising=False)
    monkeypatch.delenv("CALCULATOR_LOG_DIR", raising=False)
    monkeypatch.delenv("CALCULATOR_LOG_FILE", raising=False)
    monkeypatch.delenv("CALCULATOR_AUTO_SAVE", raising=False)
    monkeypatch.delenv("CALCULATOR_MAX_HISTORY_SIZE", raising=False)
    monkeypatch.delenv("CALCULATOR_PRECISION", raising=False)
    monkeypatch.delenv("CALCULATOR_MAX_INPUT_VALUE", raising=False)
    monkeypatch.delenv("CALCULATOR_DEFAULT_ENCODING", raising=False)

    config = CalculatorConfig.load(env_file=Path("missing-test-env"))

    assert config.history_file == Path(__file__).resolve().parents[1] / "data/history/history.csv"
    assert config.auto_save is True
    assert config.history_dir == config.history_file.parent
    assert config.log_dir == Path(__file__).resolve().parents[1] / "data/logs"
    assert config.log_file == config.log_dir / "calculator.log"
    assert config.max_history_size == 10000
    assert config.precision == 10
    assert config.max_input_value == 1_000_000_000
    assert config.default_encoding == "utf-8"


def test_config_loads_dotenv_values(monkeypatch, tmp_path):
    monkeypatch.delenv("CALCULATOR_HISTORY_FILE", raising=False)
    monkeypatch.delenv("CALCULATOR_HISTORY_DIR", raising=False)
    monkeypatch.delenv("CALCULATOR_LOG_DIR", raising=False)
    monkeypatch.delenv("CALCULATOR_LOG_FILE", raising=False)
    monkeypatch.delenv("CALCULATOR_AUTO_SAVE", raising=False)
    monkeypatch.delenv("CALCULATOR_MAX_HISTORY_SIZE", raising=False)
    monkeypatch.delenv("CALCULATOR_PRECISION", raising=False)
    monkeypatch.delenv("CALCULATOR_MAX_INPUT_VALUE", raising=False)
    monkeypatch.delenv("CALCULATOR_DEFAULT_ENCODING", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CALCULATOR_HISTORY_DIR=records\n"
        "CALCULATOR_LOG_DIR=logs\n"
        "CALCULATOR_LOG_FILE=calc.log\n"
        "CALCULATOR_HISTORY_FILE=history.csv\n"
        "CALCULATOR_MAX_HISTORY_SIZE=25\n"
        "CALCULATOR_AUTO_SAVE=false\n"
        "CALCULATOR_PRECISION=4\n"
        "CALCULATOR_MAX_INPUT_VALUE=500\n"
        "CALCULATOR_DEFAULT_ENCODING=utf-8-sig\n",
        encoding="utf-8",
    )

    config = CalculatorConfig.load(env_file)

    project_root = Path(__file__).resolve().parents[1]
    assert config.history_file == project_root / "records/history.csv"
    assert config.auto_save is False
    assert config.history_dir == project_root / "records"
    assert config.log_dir == project_root / "logs"
    assert config.log_file == config.log_dir / "calc.log"
    assert config.max_history_size == 25
    assert config.precision == 4
    assert config.max_input_value == 500
    assert config.default_encoding == "utf-8-sig"


def test_config_rejects_empty_history_path(monkeypatch):
    monkeypatch.setenv("CALCULATOR_HISTORY_FILE", " ")

    with pytest.raises(ConfigurationError, match="cannot be empty"):
        CalculatorConfig.load(env_file=Path("missing-test-env"))


def test_config_rejects_invalid_auto_save_value(monkeypatch):
    monkeypatch.setenv("CALCULATOR_AUTO_SAVE", "sometimes")

    with pytest.raises(ConfigurationError, match="must be 'true' or 'false'"):
        CalculatorConfig.load(env_file=Path("missing-test-env"))


def test_config_rejects_directory_as_history_prefix(monkeypatch, tmp_path):
    monkeypatch.setenv("CALCULATOR_HISTORY_FILE", str(tmp_path))

    with pytest.raises(ConfigurationError, match="not a directory"):
        CalculatorConfig.load(env_file=Path("missing-test-env"))


def test_config_rejects_file_as_history_parent(monkeypatch, tmp_path):
    parent_file = tmp_path / "not-a-directory"
    parent_file.write_text("x", encoding="utf-8")
    monkeypatch.setenv(
        "CALCULATOR_HISTORY_FILE", str(parent_file / "history.csv")
    )

    with pytest.raises(ConfigurationError, match="parent.*must be a directory"):
        CalculatorConfig.load(env_file=Path("missing-test-env"))


def test_config_rejects_root_without_filename(monkeypatch):
    monkeypatch.setenv("CALCULATOR_HISTORY_FILE", str(Path("/").anchor))

    with pytest.raises(ConfigurationError, match="must include a filename"):
        CalculatorConfig.load(env_file=Path("missing-test-env"))


def test_config_wraps_history_path_os_errors(monkeypatch):
    monkeypatch.setenv("CALCULATOR_HISTORY_FILE", "history.csv")

    def fail_exists(_path):
        raise OSError("cannot inspect path")

    monkeypatch.setattr(Path, "exists", fail_exists)
    with pytest.raises(ConfigurationError, match="Invalid configuration path"):
        CalculatorConfig.load(env_file=Path("missing-test-env"))


@pytest.mark.parametrize(
    "name, value, message",
    [
        ("CALCULATOR_MAX_HISTORY_SIZE", "0", "positive integer"),
        ("CALCULATOR_MAX_HISTORY_SIZE", "abc", "positive integer"),
        ("CALCULATOR_PRECISION", "-1", "nonnegative integer"),
        ("CALCULATOR_MAX_INPUT_VALUE", "inf", "positive finite number"),
        ("CALCULATOR_DEFAULT_ENCODING", "not-an-encoding", "Unknown"),
    ],
)
def test_config_rejects_invalid_settings(monkeypatch, name, value, message):
    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigurationError, match=message):
        CalculatorConfig.load(env_file=Path("missing-test-env"))


def test_config_rejects_file_used_as_log_directory(monkeypatch, tmp_path):
    not_a_directory = tmp_path / "not-a-directory"
    not_a_directory.write_text("x", encoding="utf-8")
    monkeypatch.setenv("CALCULATOR_LOG_DIR", str(not_a_directory))

    with pytest.raises(ConfigurationError, match="CALCULATOR_LOG_DIR must be a directory"):
        CalculatorConfig.load(env_file=Path("missing-test-env"))
