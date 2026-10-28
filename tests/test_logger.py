from app.logger import Logger


def test_logger_writes_warning_and_error_levels(tmp_path):
    log_file = tmp_path / "logs" / "calculator.log"
    logger = Logger(log_file)

    logger.warning("input was rejected: %s", "too large")
    logger.error("history write failed")
    logger.close()

    log_text = log_file.read_text(encoding="utf-8")
    assert "WARNING input was rejected: too large" in log_text
    assert "ERROR history write failed" in log_text