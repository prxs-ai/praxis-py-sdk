import pytest
from loguru import logger
import sys
from unittest.mock import MagicMock
from io import StringIO


@pytest.fixture
def setup_logger(mocker):
    logger.remove()
    mock_stdout = StringIO()
    mocker.patch.object(sys, "stdout", mock_stdout)
    mock_file_handler = mocker.patch("loguru.logger.add")
    logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} - {message}", level="INFO")
    logger.add("app.log", rotation="10 MB", compression="zip", level="ERROR")
    return mock_stdout, mock_file_handler


def test_info_logging(setup_logger):
    mock_stdout, _ = setup_logger
    logger.info("Test info message")
    log_output = mock_stdout.getvalue()
    assert "Test info message" in log_output
    assert "| INFO |" in log_output
    assert log_output.count("\n") == 1
    assert "test_loguru.py" in log_output


def test_error_logging(setup_logger, mocker):
    mock_stdout, mock_file_handler = setup_logger
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Test error message")
    log_output = mock_stdout.getvalue()
    assert "Test error message" in log_output
    assert "| ERROR |" in log_output
    assert "ZeroDivisionError: division by zero" in log_output
    mock_file_handler.assert_called_with(
        "app.log", rotation="10 MB", compression="zip", level="ERROR"
    )


def test_log_format(setup_logger):
    mock_stdout, _ = setup_logger
    logger.info("Formatted log test")
    log_output = mock_stdout.getvalue()
    import re
    pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| INFO \| \S+:\d+ - Formatted log test"
    assert re.match(pattern, log_output.strip())


def test_remove_default_handler(mocker):
    mock_remove = mocker.patch("loguru.logger.remove")
    logger.remove()
    mock_remove.assert_called_once()


def test_main_block(setup_logger, mocker):
    mock_stdout, _ = setup_logger
    logger.info("This is an info message.")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("An error occurred!")
    log_output = mock_stdout.getvalue()
    assert "This is an info message" in log_output
    assert "An error occurred!" in log_output
    assert "| INFO |" in log_output
    assert "| ERROR |" in log_output
    assert "ZeroDivisionError: division by zero" in log_output
