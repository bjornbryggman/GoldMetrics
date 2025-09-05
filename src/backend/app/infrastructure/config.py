# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides paths and configuration settings for the application.

This module includes:
- `PathConfig`: A class that defines and manages application paths.
- `AppConfig`: A dataclass that stores application configuration settings.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from structlog import stdlib

log = stdlib.get_logger(__name__)

# ================================================= #
#               Environment Variables               #
# ================================================= #


# Environment variables from docker-compose.yml
MESSAGE_BROKER_URL = os.getenv("MESSAGE_BROKER_URL")
IN_MEMORY_STORAGE_URL = os.getenv("IN_MEMORY_STORAGE_URL")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL")
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL")
EODHD_API_KEY = os.getenv("EODHD_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ============================================== #
#               Path Configuration               #
# ============================================== #


class PathConfig:
    """
    Manages application paths and directories.

    This class defines and initializes paths for various application resources,
    including input/output directories, databases, logs, and the pyproject.toml.

    Attributes:
        - root_path: The root directory of the application.
        - input_dir: The directory for input files.
        - database_file: The path to the database file.
        - alembic_versions_dir: The directory for Alembic versions.
        - alembic_ini: The path to the Alembic ini.
        - pyproject_toml: The path to the application settings file.
    """

    def __init__(self) -> None:
        """
        Initialize the Paths object.

        Raises:
            - OSError: If the root path cannot be resolved.
        """
        try:
            self.root_path = Path(__file__).resolve().parent.parent.parent.parent
            self.input_dir = self.root_path / "frontend" / "input_directory"
            self.backend_dir = self.root_path / "backend"
            self.alembic_versions_dir = (
                self.root_path / "backend" / "app" / "infrastructure" / "database" / "alembic" / "versions"
            )
            self.alembic_ini = self.root_path / "backend" / "app" / "infrastructure" / "database" / "alembic.ini"
            self.pyproject_toml = self.root_path / "backend" / "pyproject.toml"
        except OSError as error:
            log.exception("Error resolving root path.", exc_info=error)
            raise


# ============================================= #
#               App Configuration               #
# ============================================= #


@dataclass
class AppConfig:
    """
    Stores application configuration settings.

    This dataclass provides a centralized location for application configuration,
    including log level, database URLs, message broker URLs, and API keys.

    Attributes:
        - log_level: The logging level.
        - sqlite3_url: The URL for the SQLite3 database.
        - rabbitmq_url: The URL for the RabbitMQ message broker.
        - redis_url: The URL for the Redis server.
        - eodhd_api_key: The API key for the EODHD API.
        - telegram_bot_token: The token for the Telegram bot.
        - telegram_chat_id: The chat ID for the Telegram bot.
    """

    log_level: str = "INFO"
    async_timescaledb_url: str = field(default_factory=lambda: ASYNC_DATABASE_URL)
    sync_timescaledb_url: str = field(default_factory=lambda: SYNC_DATABASE_URL)
    rabbitmq_url: str = field(default_factory=lambda: MESSAGE_BROKER_URL)
    redis_url: str = field(default_factory=lambda: IN_MEMORY_STORAGE_URL)
    eodhd_api_key: str | None = field(default_factory=lambda: EODHD_API_KEY)
    telegram_bot_token: str | None = field(default_factory=lambda: TELEGRAM_BOT_TOKEN)
    telegram_chat_id: str | None = field(default_factory=lambda: TELEGRAM_CHAT_ID)
