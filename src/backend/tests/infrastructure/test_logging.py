# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides tests for the logging configuration.

This module includes:
- `TestLogger`:     Tests for the `initialize_logger` function and logging configuration.
"""

import json

import pytest
import structlog
from backend.app.infrastructure.logging import initialize_logger


class TestLogger:
    """
    Tests for the `initialize_logger` function and logging configuration.

    Methods:
        - test_initialize_logger_valid_output: Tests that the logger is initialized correctly and logs a message.
        - test_initialize_logger_empty_log_level: Tests that an empty log level raises a TypeError.
        - test_logging_configuration: Tests that the logger logs messages at different levels correctly.
    """

    # ====================================== #
    #               Unit Tests               #
    # ====================================== #

    async def test_initialize_logger_valid_output(self, capsys) -> None:
        """
        Test that the logger is initialized correctly and logs a message.

        Args:
            - capsys: Fixture to capture the output.

        Assertions:
            - The logger is configured.
            - The log message is captured in the output.
            - The log message is in JSON format with the correct fields.

        Raises:
            - AssertionError: If the logger is not configured or the log message is not captured correctly.
        """
        await initialize_logger("INFO")
        assert structlog.is_configured()

        logger = structlog.stdlib.get_logger()
        logger.info("This is a test log message.")

        captured_output = capsys.readouterr()

        assert "This is a test log message." in captured_output.out

        log_line = captured_output.out.splitlines()[-1]
        log_json = json.loads(log_line)

        assert log_json["event"] == "This is a test log message."
        assert "timestamp" in log_json
        assert log_json["level"] == "info"

    async def test_initialize_logger_empty_log_level(self) -> None:
        """
        Test that an empty log level raises a TypeError.

        Assertions:
            - Initializing the logger with an empty log level raises a TypeError.

        Raises:
            - AssertionError: If the TypeError is not raised.
        """
        with pytest.raises(TypeError):
            await initialize_logger("")

    async def test_logging_configuration(self, capsys) -> None:
        """
        Test that the logger logs messages at different levels correctly.

        Args:
            - capsys: Fixture to capture the output.

        Assertions:
            - The logger logs messages at the INFO and ERROR levels.
            - The log messages are in JSON format with the correct fields.

        Raises:
            - AssertionError: If the log messages are not captured correctly.
        """
        await initialize_logger("DEBUG")

        logger = structlog.get_logger()
        logger.info("Integration info :)")
        logger.error("Integration error :(")

        captured_output = capsys.readouterr().out.strip()
        lines = captured_output.splitlines()
        assert len(lines) >= 2

        info_log_line = lines[-2]
        error_log_line = lines[-1]

        info_log = json.loads(info_log_line)
        error_log = json.loads(error_log_line)

        assert info_log["event"] == "Integration info :)"
        assert error_log["level"] == "error"
        assert "timestamp" in info_log and "timestamp" in error_log
