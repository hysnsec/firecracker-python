"""Tests for Logger class."""

import pytest
import logging
from unittest.mock import patch
from firecracker.logger import Logger


class TestLogger:
    """Test Logger functionality."""

    def test_logger_success_level_colored(self):
        """Test SUCCESS level gets colored correctly"""
        logger = Logger(level="INFO")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.success = True

        result = logger._add_colored_levelname(record)
        assert result is True
        assert hasattr(record, "colored_levelname")
        assert "SUCCESS" in record.colored_levelname

    def test_logger_call_unknown_level_defaults_to_info(self):
        """Test __call__ with unknown level defaults to INFO"""
        logger = Logger(level="INFO")

        logger("UNKNOWN", "Test message with unknown level")

    def test_logger_warn_method(self):
        """Test warn method logs correctly"""
        logger = Logger(level="INFO")

        logger.warn("This is a warning")

    def test_logger_set_level_uppercase(self):
        """Test set_level handles lowercase input"""
        logger = Logger(level="info")
        assert logger.current_level == "INFO"

    def test_logger_color_for_unknown_level(self):
        """Test colored levelname for unknown level uses default color"""
        logger = Logger(level="INFO")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.levelname = "UNKNOWN"

        result = logger._add_colored_levelname(record)
        assert result is True

    def test_logger_multiple_handlers_removed(self):
        """Test that existing handlers are removed during initialization"""
        logger = Logger(level="INFO")

        initial_handler_count = len(logger.logger.handlers)
        assert initial_handler_count == 1

        logger2 = Logger(level="DEBUG")
        assert len(logger2.logger.handlers) == 1

    def test_logger_debug_method(self):
        """Test debug method logs correctly"""
        logger = Logger(level="DEBUG")

        logger.debug("This is a debug message")

    def test_logger_error_method(self):
        """Test error method logs correctly"""
        logger = Logger(level="INFO")

        logger.error("This is an error message")

    def test_logger_info_method(self):
        """Test info method logs correctly"""
        logger = Logger(level="INFO")

        logger.info("This is an info message")
