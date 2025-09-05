# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides a bootstrap script for initializing the application.

This module includes:
- `Bootstrap`: Responsible for setting up the application's infrastructure and starting services.
"""

from structlog import stdlib

from backend.app.application import services
from backend.app.infrastructure import config, logging
from backend.app.infrastructure.container import Container
from backend.app.infrastructure.database import orm

log = stdlib.get_logger(__name__)

# ============================================ #
#               Bootstrap Script               #
# ============================================ #


class Bootstrap:
    """
    Bootstrap class for initializing the application's infrastructure and starting services.

    This class is responsible for setting up the application's dependencies, initializing logging
    and database mappers, and starting the message broker and job schedulers.

    Attributes:
        - container: The dependency injection container for the application.
        - unit_of_work: The Unit of Work for managing database transactions.
        - event_bus: The event bus for publishing and subscribing to events.
        - notification: The notification service for sending notifications.
        - eod_api_client: The client for the EOD Historical Data API.

    Methods:
        - load_dependencies: Loads and wires the dependency injection container.
        - initialize_application: Initializes the application's infrastructure and starts services.
    """

    def __init__(self) -> None:
        """
        Initialize the Bootstrap class.

        This method initializes the dependency injection container and retrieves the necessary
        dependencies for the application.
        """
        self.container = self.load_dependencies()
        self.unit_of_work = self.container.unit_of_work
        self.event_bus = self.container.event_bus
        self.notification = self.container.telegram_notification
        self.eodhd_api_client = self.container.eodhd_api_client

    def load_dependencies(self) -> Container:
        """
        Load and wire the dependency injection container.

        Returns:
            - containers.DeclarativeContainer: The configured dependency injection container.

        Raises:
            - Exception: If an error occurs while loading the dependencies.
        """
        try:
            container = Container()
            container.wire()
        except Exception:
            log.exception("Error loading dependencies.")
            raise
        else:
            return container

    async def initialize_application(
        self, start_logging: bool = True, start_orm: bool = True
    ) -> None:
        """
        Initialize the application's infrastructure and start services.

        Args:
            - start_logging: Whether to initialize the logger (default: True).
            - start_orm: Whether to start the database mappers (default: True).

        Raises:
            - Exception: If an error occurs during initialization.
        """
        try:
            # Initialize the logger
            if start_logging:
                await logging.initialize_logger(config.AppConfig().log_level)
                await log.ainfo("Logger initialized successfully.")

            # Start the database mappers
            if start_orm:
                await orm.start_database_mappers()
                await log.ainfo("Database initiated successfully.")

            # Start job schedulers
            await services.JobSchedulingService(self.event_bus()).start_job_schedulers()
            await log.ainfo("Job schedulers started successfully.")

            # Start the message broker
            message_broker = services.RabbitMQService(self.event_bus())
            await message_broker.start_message_broker()
        except Exception:
            await log.aexception("Error initializing application.")
            raise
