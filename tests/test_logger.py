from datetime import datetime

from app.logger import Logger, SessionLogger


def test_logger_writes_warning_and_error_levels(tmp_path):
    log_file = tmp_path / "logs" / "calculator.log"
    logger = Logger(log_file)

    logger.warning("input was rejected: %s", "too large")
    logger.error("history write failed")
    logger.close()

    log_text = log_file.read_text(encoding="utf-8")
    assert "WARNING input was rejected: too large" in log_text
    assert "ERROR history write failed" in log_text


def test_session_logger_records_timestamped_error(tmp_path):
    session_logger = SessionLogger(tmp_path / "history.csv")
    session_logger.record_error("calculation failed")
    log_file = session_logger.close()
    lines = log_file.read_text(encoding="utf-8").splitlines()

    assert lines[1].endswith("ERROR: calculation failed")
    datetime.fromisoformat(lines[1].split(" ", 1)[0])