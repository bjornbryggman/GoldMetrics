# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides handlers for processing domain events.

This module includes:
- `EODHDHandler`: Handler for processing events related to the EOD Historical Data API.
- `NotificationHandler`: Handler for processing notification events.
"""

from structlog import stdlib

from backend.app.application import events, ports, services
from backend.app.infrastructure.bootstrap import Bootstrap

log = stdlib.get_logger(__name__)
bootstrap = Bootstrap()

# ================================= #
#               EODHD               #
# ================================= #


class EODHDHandler(ports.AbstractEventHandler):
    """
    Handler for processing events related to the EOD Historical Data API.

    This class is responsible for handling the `UpdateFinancialInstruments` event
    and delegating the actual work to the `EODHDService`.

    Attributes:
        - unit_of_work: The Unit of Work for managing database transactions.
        - event_bus: The event bus for publishing notifications.
        - api_client: The API client for making HTTP requests.

    Methods:
        - handle: Handles the `UpdateFinancialInstruments` event by initiating
            a daily scan of financial instruments.
    """

    def __init__(
        self,
        unit_of_work: ports.AbstractUnitOfWork = bootstrap.unit_of_work,
        event_bus: ports.AbstractEventBus = bootstrap.event_bus,
        api_client: ports.AbstractAPIClient = bootstrap.eodhd_api_client,
    ) -> None:
        """
        Initialize the EODHDHandler.

        Args:
            - unit_of_work: The Unit of Work for managing database transactions.
            - event_bus: The event bus for publishing notifications.
            - api_client: The API client for making HTTP requests.
        """
        self.unit_of_work = unit_of_work
        self.event_bus = event_bus
        self.api_client = api_client

    @property
    def event_type(self) -> str:
        """
        Return the event type this handler is responsible for.

        Returns:
            - str: The event type.
        """
        return "UpdateFinancialInstruments"

    async def handle(self, message: events.UpdateFinancialInstruments) -> None:
        """
        Handle the `UpdateFinancialInstruments` event.

        This method initiates a scan of financial instruments using the `EODHDService`.

        Args:
            - message: The `UpdateFinancialInstruments` event.

        Raises:
            - Exception: If an error occurs during the handling of the event.
        """
        try:
            if message:
                await log.ainfo("Initiating scan of financial instruments ...")
                await services.EODHDService(
                    unit_of_work=self.unit_of_work,
                    event_bus=self.event_bus,
                    api_client=self.api_client,
                ).update_financial_instruments()
        except Exception:
            await log.aexception("Error handling 'UpdateFinancialInstruments' event.")
            raise


# ========================================= #
#               Notifications               #
# ========================================= #


class NotificationHandler(ports.AbstractEventHandler):
    """
    Handler for processing notification events.

    This class is responsible for handling notification events by sending the notification
    using the provided notification sender.

    Attributes:
        - sender: The notification sender for sending notifications.

    Methods:
        - handle: Handles an incoming notification event by sending the notification.
    """

    def __init__(
        self, sender: ports.AbstractNotification = bootstrap.notification
    ) -> None:
        """
        Initialize the NotificationHandler.

        Args:
            - sender: The notification sender for sending notifications.
        """
        self.sender = sender()

    @property
    def event_type(self) -> str:
        """
        Return the event type this handler is responsible for.

        Returns:
            - str: The event type.
        """
        return "Notification"

    async def handle(self, message: events.Notification) -> None:
        """
        Handle the `Notification` event.

        This method routes incoming notifications to a dedicated sender.

        Args:
            - message: The `Notification` event.

        Raises:
            - Exception: If an error occurs while sending the notification.
        """
        try:
            if message:
                await log.ainfo("Sending notification ...")
                await self.sender.send_notification(message.text)
        except Exception:
            await log.aexception("Error handling 'Notification' event.")
            raise
