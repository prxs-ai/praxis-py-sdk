import os
import re
from io import StringIO
import sys
from unittest.mock import patch
import pytest
from loguru import logger


@pytest.fixture
def clean_logs():
    logger.remove()
    yield
    logger.remove()
    if os.path.exists("app.log"):
        os.remove("app.log")


def test_logger_stdout_output(clean_logs):
    with patch('sys.stdout', new=StringIO()) as fake_out:
        logger.add(sys.stdout, format="{message}", level="INFO")
        logger.info("Test message")
        output = fake_out.getvalue().strip()
        assert "Test message" in output


def test_logger_file_output(clean_logs):
    logger.add("app.log", format="{message}", level="ERROR")
    logger.error("Test error message")
    assert os.path.exists("app.log")
    with open("app.log", "r") as f:
        content = f.read()
        assert "Test error message" in content


def test_logger_exception_handling(clean_logs):
    with patch('sys.stderr', new=StringIO()) as fake_err:
        logger.add(sys.stderr, format="{message}", level="ERROR")
        try:
            1 / 0
        except ZeroDivisionError:
            logger.exception("Division error")
        error_output = fake_err.getvalue().strip()
        assert "Division error" in error_output
        assert "ZeroDivisionError" in error_output


def test_logger_format(clean_logs):
    with patch('sys.stdout', new=StringIO()) as fake_out:
        logger.add(sys.stdout, format="{time} | {level} | {message}", level="INFO")
        logger.info("Formatted message")
        output = fake_out.getvalue().strip()
        assert "| INFO | Formatted message" in output
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", output.split(" | ")[0])


def test_logger_level_filtering(clean_logs):
    with patch('sys.stdout', new=StringIO()) as fake_out:
        logger.add(sys.stdout, format="{message}", level="WARNING")
        logger.info("This should not appear")
        logger.warning("This should appear")
        output = fake_out.getvalue().strip()
        assert "This should not appear" not in output
        assert "This should appear" in output

