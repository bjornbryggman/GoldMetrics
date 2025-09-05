# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides logging configuration for the application.

This module includes:
- `initialize_logger`: Configures and initializes the logger with structlog.
"""

import logging
import sys

import structlog

# =================================== #
#               Logging               #
# =================================== #


async def initialize_logger(log_level: str) -> None:
    """
    Initialize and configure the logger with `structlog`.

    This function sets up `structlog` with a predefined set of processors and configures
    the logging level and output format. It also ensures that the logger is cached for
    performance optimization.

    Args:
        - log_level: The logging level to set (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").

    Raises:
        - TypeError: If the log_level is not provided.
        - ValueError: If the log_level is invalid.
    """
    if not log_level:
        raise TypeError

    # Configure structlog with processors
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure the logging level and output format
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=log_level, force=True
    )
