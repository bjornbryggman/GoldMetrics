# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides asynchronous `AbstractAPIClient` adapters using AIOHTTP.

This module includes:
- `RateLimiter`: Token bucket rate limiter.
- `AIOHTTPAPIClientAdapter`: Asynchronous HTTP client with rate limiting and retry capabilities.
- `EODHDAPIClient`: Asynchronous HTTP client for interacting with the EOD Historical Data API.
"""

import asyncio
import contextlib
from typing import Any, Self

import aiohttp
from structlog import stdlib
from tenacity import (
    WrappedFn,
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.application.ports import AbstractAPIClient

log = stdlib.get_logger(__name__)

# ======================================== #
#               Rate Limiter               #
# ======================================== #


class RateLimiter:
    """
    Token bucket rate limiter.

    This class implements a token bucket algorithm to enforce rate limits on asynchronous operations,
    ensuring that the number of requests does not exceed the specified limit within a given interval.

    Attributes:
        - rate_limit: The maximum number of requests allowed per interval.
        - delay: The delay between token refills.
        - queue: A queue to hold available tokens.
        - _task: The background task responsible for refilling tokens.
        - _active: A flag indicating whether the rate limiter is active.

    Methods:
        - _fill_tokens: Continuously adds tokens to the bucket at a fixed rate.
        - acquire: Acquires a token from the bucket, blocking if necessary.
        - stop: Stops the token-filling task.
    """

    def __init__(self, rate_limit: int, interval: int) -> None:
        """
        Initialize the RateLimiter.

        Args:
            - rate_limit: The maximum number of requests allowed per interval.
            - interval: The time interval (in seconds) for the rate limit.
        """
        self.rate_limit = rate_limit
        self.delay = interval / rate_limit
        self.queue = asyncio.Queue(maxsize=rate_limit)
        self._task = asyncio.create_task(self._fill_tokens())
        self._active = True

    async def _fill_tokens(self) -> None:
        "Continuously refill tokens at the specified rate."
        while self._active:
            await asyncio.sleep(self.delay)
            with contextlib.suppress(asyncio.QueueFull):
                self.queue.put_nowait(1)

    async def acquire(self) -> None:
        "Acquire a token before making a request."
        await self.queue.get()

    async def stop(self) -> None:
        "Stop the rate limiter."
        self._active = False
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task


# ============================================== #
#               Generic API Client               #
# ============================================== #


class AIOHTTPAPIClientAdapter(AbstractAPIClient):
    """
    Asynchronous HTTP client using AIOHTTP.

    This class implements the `AbstractAPIClient` interface by providing a robust and configurable
    HTTP client for making API requests. It includes features such as rate limiting, exponential
    backoff retries, and timeout management.

    Attributes:
        - rate_limit: Optional maximum requests per minute.
        - timeout: Request timeout in seconds.
        - max_retries: Maximum number of retry attempts.
        - backoff_start: Initial backoff delay in seconds.
        - rate_limiter: An instance of `RateLimiter` for enforcing rate limits.
        - session: The aiohttp `ClientSession` for making HTTP requests.

    Methods:
        - request: Makes an asynchronous HTTP request with retry capabilties and rate limiting.
        - __aenter__: Enter the context manager and initialize the session.
        - __aexit__: Exit the context manager and clean up resources.
    """

    def __init__(
        self,
        rate_limit: int | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_start: float = 1.0,
    ) -> None:
        """
        Initialize the GenericAPIClient.

        Args:
            - rate_limit: Optional maximum requests per minute.
            - timeout: Request timeout in seconds.
            - max_retries: Maximum number of retry attempts.
            - backoff_start: Initial backoff delay in seconds.
        """
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_start = backoff_start
        self.rate_limiter = RateLimiter(rate_limit, 60) if rate_limit else None
        self.session: aiohttp.ClientSession | None = None
        self.retry_config = retry(
            retry=retry_if_exception(
                lambda error: isinstance(error, aiohttp.ClientError)
            ),
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=backoff_start),
            before_sleep=before_sleep_log(log, 30),
        )

    @property
    def request(self) -> WrappedFn:
        """
        Property that wraps the request method with the retry configuration.

        Returns:
            - The retry-wrapped request method.
        """
        return self.retry_config(self._request)

    async def _request(
        self, url: str, method: str = "GET", **kwargs: dict[str, Any] | None
    ) -> dict[str, Any]:
        """
        Make an asynchronous HTTP request with retry capabilties and rate limiting.

        Args:
            - method: The HTTP method to use (e.g., "GET", "POST").
            - url: The URL to send the request to.
            - **kwargs: Optional request parameters (headers, json, params, etc.).

        Returns:
            - dict[str, Any]: The parsed JSON response from the API.

        Raises:
            - aiohttp.ClientResponseError: Raised when the HTTP response status code indicates an error.
            - aiohttp.ClientError: Raised for other unrecoverable request failures.
        """
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        try:
            await log.adebug("Making HTTP request: %s, %s", method, url)
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as error:
            await log.aexception("HTTP error occurred: %s", error.status)
            raise
        except aiohttp.ClientError:
            await log.aexception("Request (%s, %s) failed.", method, url)
            raise

    async def __aenter__(self) -> Self:
        """
        Enter the context manager and initialize the session.

        Returns:
            - Self: The instance of the GenericAPIClient.
        """
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """
        Exit the context manager and clean up resources.

        Args:
            - *exc_info: Exception information if an exception occurred.
        """
        await self.session.close()

        if self.rate_limiter:
            await self.rate_limiter.stop()


# ========================================================== #
#               EOD Historical Data API Client               #
# ========================================================== #


class EODHDAPIClient(AIOHTTPAPIClientAdapter):
    """
    Asynchronous HTTP client for the EOD Historical Data API.

    This class extends the `AIOHTTPAPIClientAdapter` to provide methods for interacting with
    the EOD Historical Data API, including fetching exchanges, tickers, historical data,
    and bulk end-of-day data.

    Attributes:
        - api_key: The API key for accessing the EOD Historical Data API.

    Methods:
        - `get_exchanges`: Fetches the list of available exchanges.
        - `get_tickers`: Fetches tickers for a specific exchange, optionally including delisted tickers.
        - `get_historical_data`: Fetches historical data for a specific ticker.
        - `get_eod_bulk_data`: Fetches bulk end-of-day data for a specific exchange.
    """

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        """
        Initialize the EODHDAPIClient.

        Args:
            - api_key: The API key for accessing the EOD Historical Data API.
            - **kwargs: Additional arguments to pass to the parent class.

        Raises:
            - ValueError: If the API key is missing or empty.
        """
        super().__init__(**kwargs)
        if not api_key:
            log.exception("API key is required for EODHDAPIClient")
            raise ValueError
        self.api_key = api_key

    async def get_exchanges(self) -> list[dict]:
        """
        Fetch the list of available exchanges.

        Returns:
            - list[dict]: A list of available exchanges.

        Raises:
            - Exception: If an error occurs during the request.
        """
        try:
            params = {"api_token": self.api_key, "fmt": "json"}
            request = await self.request(
                url="https://eodhd.com/api/exchanges-list/", method="GET", params=params
            )
        except Exception:
            await log.aexception("Error occurred during the 'get_exchanges' request")
            raise
        else:
            return request

    async def get_tickers(
        self, exchange_code: str, delisted: bool = False
    ) -> list[dict]:
        """
        Fetch tickers for a specific exchange, optionally including delisted tickers.

        Args:
            - exchange_code: The code of the exchange to fetch tickers for.
            - delisted: Whether to include delisted tickers.

        Returns:
            - list[dict]: A list of tickers for the specified exchange.

        Raises:
            - Exception: If an error occurs during the request.
        """
        try:
            params = {
                "api_token": self.api_key,
                "fmt": "json",
                "delisted": "1" if delisted else None,
            }
            request = await self.request(
                url=f"https://eodhd.com/api/exchange-symbol-list/{exchange_code}",
                method="GET",
                params=params,
            )
        except Exception:
            await log.aexception("Error occurred during the 'get_tickers' request")
            raise
        else:
            return request

    async def get_historical_data(self, ticker_code: str) -> list[dict]:
        """
        Fetch historical data for a specific ticker.

        Args:
            - ticker_code: The code of the ticker to fetch historical data for.

        Returns:
            - list[dict]: A list of historical data for the specified ticker.

        Raises:
            - Exception: If an error occurs during the request.
        """
        try:
            params = {"api_token": self.api_key, "fmt": "json"}
            request = await self.request(
                url=f"https://eodhd.com/api/eod/{ticker_code}",
                method="GET",
                params=params,
            )
        except Exception:
            await log.aexception(
                "Error occurred during the 'get_historical_data' request"
            )
            raise
        else:
            return request

    async def get_eod_bulk_data(self, exchange_code: str) -> list[dict]:
        """
        Fetch bulk end-of-day data for a specific exchange.

        Args:
            - exchange_code: The code of the exchange to fetch bulk end-of-day data for.

        Returns:
            - list[dict]: A list of bulk end-of-day data for the specified exchange.

        Raises:
            - Exception: If an error occurs during the request.
        """
        try:
            params = {"api_token": self.api_key, "fmt": "json", "filter": "extended"}
            request = await self.request(
                url=f"https://eodhd.com/api/eod-bulk-last-day/{exchange_code}",
                method="GET",
                params=params,
            )
        except Exception:
            await log.aexception(
                "Error occurred during the 'get_eod_bulk_data' request"
            )
            raise
        else:
            return request
