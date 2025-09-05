# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides abstract interfaces for API clients, event handling, notifications, and database operations.

This module includes:
- `AbstractAPIClient`: Abstract interface for an API client.
- `Event`: Base class for domain events.
- `AbstractEventBus`: Abstract interface for an event bus.
- `AbstractEventStore`: Abstract interface for tracking processed events.
- `AbstractEventHandler`: Abstract interface for event handlers.
- `AbstractNotification`: Abstract interface for sending notifications.
- `AbstractFIARRepository`: Abstract interface for the FinancialInstrument aggregate root.
- `AbstractUnitOfWork`: Abstract base class for a Unit of Work.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Self
from uuid import uuid4

from structlog import stdlib

from backend.app.domain import models

log = stdlib.get_logger(__name__)

# ====================================== #
#               API Client               #
# ====================================== #


class AbstractAPIClient(ABC):
    """
    Abstract interface for an API client.

    Methods:
        - request: Executes an HTTP request and returns the parsed response.
        - get: Executes a GET request.
        - post: Executes a POST request.
        - __aenter__: Enters the context manager.
        - __aexit__: Exits the context manager.
    """

    @abstractmethod
    async def request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """
        Execute an HTTP request and return parsed response.

        Args:
            - method: The HTTP method to use (e.g., "GET", "POST").
            - url: The URL to send the request to.
            - **kwargs: Additional arguments to pass to the request.

        Returns:
            - dict[str, Any]: The parsed response from the API.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    async def get(self, url: str, **kwargs) -> dict[str, Any]:
        """
        Execute a GET request.

        Args:
            - url: The URL to send the GET request to.
            - **kwargs: Additional arguments to pass to the request.

        Returns:
            - dict[str, Any]: The parsed response from the API.
        """
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> dict[str, Any]:
        """
        Execute a POST request.

        Args:
            - url: The URL to send the POST request to.
            - **kwargs: Additional arguments to pass to the request.

        Returns:
            - dict[str, Any]: The parsed response from the API.
        """
        return await self.request("POST", url, **kwargs)

    @abstractmethod
    async def __aenter__(self) -> Self:
        """
        Enter the context manager.

        Returns:
            - Self: The instance of the API client.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *exc_info) -> None:
        """
        Exit the context manager.

        Args:
            - *exc_info: Exception information if an exception occurred.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError


# ================================== #
#               Events               #
# ================================== #


@dataclass(frozen=True)
class Event:
    """
    Base class for domain events.

    This class provides a common structure for all domain events, including
    a unique event ID, an event type, and a timestamp indicating when the event occurred.

    Attributes:
        - event_id: A unique identifier for the event.
        - event_type: The type of the event, automatically set based on the class name.
        - occurred_on: The timestamp when the event occurred.

    Methods:
        - __post_init__: Automatically sets the event type based on the class name.
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = field(init=False)
    occurred_on: str = field(default_factory=lambda: str(datetime.now(UTC)))

    def __post_init__(self) -> None:
        """
        Automatically set the event type based on the class name.

        This method is called after the object is initialized, and it sets the `event_type`
        attribute to the name of the class.
        """
        object.__setattr__(self, "event_type", self.__class__.__name__)


class AbstractEventStore(ABC):
    """
    Abstract interface for tracking processed events.

    This class defines the interface for checking if an event has been processed
    and for marking an event as processed. Subclasses must implement these methods
    to provide specific functionality.

    Methods:
        - is_processed: Checks if an event has already been processed.
        - mark_as_processed: Marks an event as processed.
    """

    @abstractmethod
    async def is_processed(self, event_id: str) -> bool:
        """
        Check if an event has already been processed.

        Args:
            - event_id: The unique identifier of the event.

        Returns:
            - bool: True if the event has been processed, False otherwise.

        Raises:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_as_processed(self, event_id: str) -> None:
        """
        Mark an event as processed.

        Args:
            - event_id: The unique identifier of the event.

        Raises:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError


class AbstractEventBus(ABC):
    """
    Abstract interface for an event bus.

    Methods:
        - publish: Publishes an event.
        - subscribe: Subscribes to an event and processes it with a provided handler.
        - __aenter__: Enters the context manager.
        - __aexit__: Exits the context manager.
    """

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """
        Publish an event.

        Args:
            - event: The event to be published, must inherit from 'Event'.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def subscribe(
        self,
        event_name: str,
        handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Subscribe to an event and process it with the provided handler.

        Args:
            - event_name: The name of the event to subscribe to.
            - handler: An asynchronous callable that processes the event data.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> Self:
        """
        Enter the context manager.

        Returns:
            - AbstractEventBus: The event bus instance.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager.

        Args:
            - exc_type: The type of the exception, if any.
            - exc_val: The exception instance, if any.
            - exc_tb: The traceback, if any.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError


class AbstractEventHandler(ABC):
    """
    Abstract interface for event handlers.

    This class defines the interface for handling events of a specific type.
    Subclasses must implement the `event_type` property and the `handle` method.

    Methods:
        - event_type: Returns the event type this handler is responsible for.
        - handle: Handles the incoming message.
    """

    @property
    @abstractmethod
    def event_type(self) -> str:
        """
        Return the event type this handler is responsible for.

        Returns:
            - str: The event type.

        Exceptions:
            - NotImplementedError: Raised when the property is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def handle(self, message: Any) -> None:
        """
        Handle the incoming message.

        Args:
            - message: The message to handle.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError


# ========================================= #
#               Notifications               #
# ========================================= #


class AbstractNotification(ABC):
    """
    Abstract interface for sending notifications.

    Methods:
        - send_notification: Sends a notification.
    """

    @abstractmethod
    async def send_notification(self, text: str) -> None:
        """
        Send a notification.

        Args:
            - text: The text content of the notification.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError


# ====================================== #
#               Repository               #
# ====================================== #


class AbstractFIARRepository(ABC):
    """
    Abstract interface for the FinancialInstrument aggregate root.

    Methods:
        - get_ticker: Retrieves a ticker by its code.
        - get_exchange: Retrieves an exchange by its code.
        - get_historical_data: Retrieves historical data for a ticker within a specified date range.
        - get_technical_data; Retrieves technical data for a ticker.
        - get_ticker_with_technical_and_historical_data: Retrieves a ticker along with its technical and historical data.
        - update_technical_data: Updates technical data for a ticker.
        - add_ticker: Adds a new ticker to the repository.
        - add_exchange: Adds a new exchange to the repository.
        - add_historical_data: Adds historical data for a ticker.
        - add_historical_data_bulk: Adds multiple historical data entries in bulk.
        - add_technical_data: Adds technical data for a ticker.
    """

    @abstractmethod
    async def get_ticker(self, code: str) -> models.Ticker:
        """
        Retrieve a ticker by its code.

        Args:
            - code: The code of the ticker to retrieve.

        Returns:
            - model.Ticker: The retrieved ticker.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_exchange(self, code: str) -> models.Exchange:
        """
        Retrieve an exchange by its code.

        Args:
            - code: The code of the exchange to retrieve.

        Returns:
            - model.Exchange: The retrieved exchange.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_historical_data(
        self, code: str, start_date: str | None = None, end_date: str | None = None
    ) -> list[models.HistoricalData]:
        """
        Retrieve historical data for a ticker within a specified date range.

        Args:
            - code: The code of the ticker to retrieve historical data for.
            - start_date: The start date of the range (optional).
            - end_date: The end date of the range (optional).

        Returns:
            - list[model.HistoricalData]: The retrieved historical data.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_technical_data(self, code: str) -> models.TechnicalData:
        """
        Retrieve technical data for a ticker.

        Args:
            - code: The code of the ticker to retrieve technical data for.

        Returns:
            - model.TechnicalData: The retrieved technical data.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_ticker_with_technical_and_historical_data(
        self, code: str, start_date: str | None = None, end_date: str | None = None
    ) -> tuple[models.Ticker, models.TechnicalData, list[models.HistoricalData]]:
        """
        Retrieve a ticker along with its technical and historical data.

        Args:
            - code: The code of the ticker to retrieve.
            - start_date: The start date of the historical data range (optional).
            - end_date: The end date of the historical data range (optional).

        Returns:
            - tuple[model.Ticker, model.TechnicalData, list[model.HistoricalData]]: The retrieved ticker, technical data, and historical data.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_technical_data(self, technical_data: models.TechnicalData) -> None:
        """
        Update technical data for a ticker.

        Args:
            - technical_data: The technical data to update.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def add_ticker(self, ticker: models.Ticker) -> None:
        """
        Add a new ticker to the repository.

        Args:
            - ticker: The ticker to add.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def add_exchange(self, exchange: models.Exchange) -> None:
        """
        Add a new exchange to the repository.

        Args:
            - exchange: The exchange to add.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def add_historical_data(self, historical_data: models.HistoricalData) -> None:
        """
        Add historical data for a ticker.

        Args:
            - historical_data: The historical data to add.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def add_historical_data_bulk(
        self, historical_data_list: list[models.HistoricalData]
    ) -> None:
        """
        Add multiple historical data entries in bulk.

        Args:
            - historical_data_list: The list of historical data entries to add.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def add_technical_data(self, technical_data: models.TechnicalData) -> None:
        """
        Add technical data for a ticker.

        Args:
            - technical_data: The technical data to add.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError


# ======================================== #
#               Unit of Work               #
# ======================================== #


class AbstractUnitOfWork(ABC):
    """
    Abstract base class for a Unit of Work.

    Methods:
        - commit: Commits changes to the database.
        - rollback: Rolls back changes to the database.
        - __aenter__: Enters the context manager.
        - __aexit__: Exits the context manager.
    """

    financial_instrument: AbstractFIARRepository

    @abstractmethod
    async def commit(self) -> None:
        """
        Commit changes to the database.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        """
        Roll back changes to the database.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> Self:
        """
        Enter the context manager.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager and roll back changes if an exception occurred.

        Args:
            - exc_type: The type of the exception, if any.
            - exc_val: The exception instance, if any.
            - exc_tb: The traceback, if any.

        Exceptions:
            - NotImplementedError: Raised when the method is not implemented by a subclass.
        """
        raise NotImplementedError
