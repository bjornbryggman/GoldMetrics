# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides unit and integration tests for the `RateLimiter` and `AIOHTTPAPIClientAdapter` classes.

This module includes:
- `FakeResponse`: A fake response class for simulating HTTP responses in tests.
- `FakeErrorContextManager`: A fake context manager for simulating errors in tests.
- `TestRateLimiter`: Tests for the `RateLimiter` class.
- `TestAIOHTTPAPIClientAdapter`: Tests for the `AIOHTTPAPIClientAdapter` class.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from tenacity import RetryError

from backend.app.infrastructure.adapters.api import RateLimiter, AIOHTTPAPIClientAdapter

# ================================= #
#               Fakes               #
# ================================= #


class FakeResponse:
    """
    A fake response class for simulating HTTP responses in tests.

    Attributes:
        - status: The HTTP status code of the response.
        - _json_data: The JSON data to be returned by the response.
        - request_info: Mocked request information.

    Methods:
        - json: Returns the JSON data.
        - raise_for_status: Raises an exception if the status code indicates an error.
        - __aenter__: Enters the context manager.
        - __aexit__: Exits the context manager.
    """

    def __init__(self, status: int, json_data: dict):
        """
        Initialize the FakeResponse.

        Args:
            - status: The HTTP status code of the response.
            - json_data: The JSON data to be returned by the response.
        """
        self.status = status
        self._json_data = json_data
        self.request_info = MagicMock(real_url="http://example.com")

    async def json(self) -> dict:
        """
        Return the JSON data.

        Returns:
            - dict: The JSON data.
        """
        return self._json_data

    def raise_for_status(self) -> None:
        """
        Raise an exception if the status code indicates an error.

        Raises:
            - aiohttp.ClientResponseError: If the status code is 400 or higher.
        """
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=self.request_info,
                history=None,
                status=self.status,
                message="Error",
                headers=None,
            )

    async def __aenter__(self):
        """
        Enter the context manager.

        Returns:
            - Self: The instance of the FakeResponse.
        """
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Exit the context manager.

        Args:
            - exc_type: The type of the exception, if any.
            - exc: The exception instance, if any.
            - tb: The traceback, if any.
        """
        pass


class FakeErrorContextManager:
    """
    A fake context manager for simulating errors in tests.

    Attributes:
        - exception: The exception to raise when the context is entered.

    Methods:
        - __aenter__: Raises the exception when the context is entered.
        - __aexit__: Exits the context manager.
    """

    def __init__(self, exception: Exception):
        """
        Initialize the FakeErrorContextManager.

        Args:
            - exception: The exception to raise when the context is entered.
        """
        self.exception = exception

    async def __aenter__(self):
        """
        Raise the exception when the context is entered.

        Raises:
            - Exception: The exception passed during initialization.
        """
        raise self.exception

    async def __aexit__(self, exc_type, exc, tb):
        """
        Exit the context manager.

        Args:
            - exc_type: The type of the exception, if any.
            - exc: The exception instance, if any.
            - tb: The traceback, if any.
        """
        pass


# ================================= #
#               Tests               #
# ================================= #


class TestRateLimiter:
    """
    Tests for the `RateLimiter` class.

    Methods:
        - test_rate_limiter_token_generation: Tests that the RateLimiter adds tokens over time and that `acquire()` properly removes one.
        - test_rate_limiter_stop: Tests that stopping the limiter cancels the background refilling task.
    """

    # ====================================== #
    #               Unit Tests               #
    # ====================================== #

    async def test_rate_limiter_token_generation(self):
        """
        Test that RateLimiter adds tokens over time and that `acquire()` properly removes one.

        Assertions:
            - After waiting, the token queue size increases by at least one from its initial count.
            - After calling `acquire()`, the token queue size decreases by one.

        Raises:
            - AssertionError: If the token generation or acquisition does not behave as expected.
        """
        limiter = RateLimiter(rate_limit=10, interval=1)
        try:
            initial_qsize = limiter.queue.qsize()
            await asyncio.sleep(0.15)
            after_sleep = limiter.queue.qsize()
            assert after_sleep >= initial_qsize + 1

            await limiter.acquire()
            assert limiter.queue.qsize() == after_sleep - 1
        finally:
            await limiter.stop()

    async def test_rate_limiter_stop(self):
        """
        Test that stopping the limiter cancels the background refilling task.

        Assertions:
            - After stopping, the limiter's active flag (_active) is set to False.
            - The background task is either cancelled or has finished.

        Raises:
            - AssertionError: If the background task is not cancelled or stopped.
        """
        limiter = RateLimiter(rate_limit=5, interval=1)
        await limiter.stop()
        assert limiter._active is False
        assert limiter._task.cancelled() or limiter._task.done()


class TestAIOHTTPAPIClientAdapter:
    """
    Tests for the `AIOHTTPAPIClientAdapter` class.

    Methods:
        - test_api_client_successful_request: Tests that a successful HTTP request returns the expected JSON response.
        - test_api_client_retry_request: Tests that on a transient aiohttp.ClientError (simulated), the client retries the request and eventually returns a successful response.
        - test_api_client_error_response: Tests that if the HTTP response status indicates an error (>=400), the client raises an aiohttp.ClientResponseError.
        - test_api_client_context_manager: Tests that the AIOHTTPAPIClientAdapter properly creates and closes its session.
        - test_api_client_rate_limiter_integration: Tests that when a rate limit is set, the client's request method waits on the rate limiter.
    """

    # ====================================== #
    #               Unit Tests               #
    # ====================================== #

    async def test_api_client_successful_request(self):
        """
        Test that a successful HTTP request returns the expected JSON response.

        Assertions:
            - The returned JSON response matches {"key": "value"}.

        Raises:
            - AssertionError: If the response does not match the expected JSON data.
        """
        async with AIOHTTPAPIClientAdapter(rate_limit=None, timeout=5) as client:
            # Monkey-patch session.request to always return a valid FakeResponse.
            client.session.request = lambda method, url, **kwargs: FakeResponse(
                200, {"key": "value"}
            )
            result = await client.request("http://example.com", method="GET")
            assert result == {"key": "value"}

    async def test_api_client_retry_request(self):
        """
        Test that on a transient aiohttp.ClientError (simulated), the client retries the request and eventually returns a successful response.

        Assertions:
            - The returned JSON response is {"retry": "succeeded"}.
            - The request is attempted exactly two times.

        Raises:
            - AssertionError: If the retry mechanism does not behave as expected.
        """
        async with AIOHTTPAPIClientAdapter(
            rate_limit=None, timeout=5, max_retries=2, backoff_start=0.01
        ) as client:
            call_count = 0

            def fake_request(method, url, **kwargs):
                nonlocal call_count
                if call_count == 0:
                    call_count += 1
                    return FakeErrorContextManager(
                        aiohttp.ClientError("Temporary error.")
                    )
                else:
                    call_count += 1
                    return FakeResponse(200, {"retry": "succeeded"})

            client.session.request = fake_request
            result = await client.request("http://example.com", method="GET")
            assert result == {"retry": "succeeded"}
            # Verify that exactly two attempts were made.
            assert call_count == 2

    async def test_api_client_error_response(self):
        """
        Test that if the HTTP response status indicates an error (>=400), the client raises an aiohttp.ClientResponseError.

        Assertions:
            - A RetryError is raised, where the underlying exception is an aiohttp.ClientResponseError with a status of 400.

        Raises:
            - AssertionError: If the expected exception is not raised.
        """
        async with AIOHTTPAPIClientAdapter(rate_limit=None, timeout=5) as client:
            # Return a response with a 400 error.
            client.session.request = lambda method, url, **kwargs: FakeResponse(400, {})
            with pytest.raises(RetryError) as exc_info:
                await client.request("http://example.com", method="GET")

            # Get the underlying exception from the last attempt.
            last_exception = exc_info.value.last_attempt.exception()
            assert isinstance(last_exception, aiohttp.ClientResponseError)
            assert last_exception.status == 400

    async def test_api_client_context_manager(self):
        """
        Test that the AIOHTTPAPIClientAdapter properly creates and closes its session.

        Assertions:
            - Within the context manager, the session is initialized and open.
            - After exiting the context, the session is closed.

        Raises:
            - AssertionError: If the session is not properly created or closed.
        """
        client = AIOHTTPAPIClientAdapter(rate_limit=None, timeout=5)
        async with client:
            assert client.session is not None
            # While inside the context, the session should be open.
            assert not client.session.closed
        # After exiting the context, the session should be closed.
        assert client.session.closed

    # ============================================= #
    #               Integration Tests               #
    # ============================================= #

    @pytest.mark.integration
    async def test_api_client_rate_limiter_integration(self):
        """
        Test that when a rate limit is set, the client's request method waits on the rate limiter.

        Assertions:
            - The rate limiter's acquire method is awaited exactly once.
            - The returned JSON response matches {"rate": "limited"}.

        Raises:
            - AssertionError: If the rate limiter is not used as expected.
        """
        async with AIOHTTPAPIClientAdapter(rate_limit=5, timeout=5) as client:
            # Replace the rate limiter's acquire() with an AsyncMock to track its usage.
            dummy_acquire = AsyncMock()
            client.rate_limiter.acquire = dummy_acquire
            # Monkey-patch the session.request to return a successful FakeResponse.
            client.session.request = lambda method, url, **kwargs: FakeResponse(
                200, {"rate": "limited"}
            )
            result = await client.request("http://example.com", method="GET")
            dummy_acquire.assert_awaited_once()
            assert result == {"rate": "limited"}
