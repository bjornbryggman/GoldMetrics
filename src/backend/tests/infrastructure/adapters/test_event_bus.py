# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides unit tests for the `TestRedisEventStoreAdapter` class.

This module includes:
- `TestRedisEventStoreAdapter`: Tests for the `RedisEventStoreAdapter` class.
"""

import pytest
from unittest.mock import AsyncMock, patch
import redis.asyncio

from backend.app.infrastructure.adapters.event_bus import RedisEventStoreAdapter

class TestRedisEventStoreAdapter:
    """
    Tests for the `RedisEventStoreAdapter` class.

    Methods:
        - test_initialize_creates_idempotent_connection: Tests that the `initialize` method creates a Redis connection and is idempotent.
        - test_initialize_raises_redis_error: Tests that the `initialize` method raises a RedisError when connection fails.
        - test_is_processed_returns_true_when_event_exists: Tests that the `is_processed` method returns True when the event exists.
        - test_is_processed_returns_false_when_event_does_not_exist: Tests that the `is_processed` method returns False when the event does not exist.
        - test_is_processed_raises_redis_error: Tests that the `is_processed` method raises a RedisError when querying Redis fails.
        - test_mark_as_processed_sets_event_with_expiration: Tests that the `mark_as_processed` method sets the event with an expiration.
        - test_mark_as_processed_raises_redis_error: Tests that the `mark_as_processed` method raises a RedisError when setting the event fails.
        - test_close_closes_redis_connection: Tests that the `close` method closes the Redis connection.
        - test_close_raises_redis_error: Tests that the `close` method raises a RedisError when closing the connection fails.
    """
    # ====================================== #
    #               Unit Tests               #
    # ====================================== #

    async def test_initialize_creates_idempotent_connection(self):
        """
        Test that the `initialize` method creates a Redis connection and is idempotent.

        Assertions:
            - The `initialize` method is called exactly once with the correct URL.
            - Subsequent calls to `initialize` do not create additional connections.

        Raises:
            - AssertionError: If the connection is not created or idempotency is not maintained.
        """
        with patch('redis.asyncio.Redis.from_url', new_callable=AsyncMock) as mock_from_url:
            event_store = RedisEventStoreAdapter('redis://test')
            await event_store.initialize()
            mock_from_url.assert_called_once_with('redis://test')

            # Call initialize a second time to verify idempotency
            await event_store.initialize()
            mock_from_url.assert_called_once_with('redis://test')

    async def test_initialize_raises_redis_error(self):
        """
        Test that the `initialize` method raises a RedisError when connection fails.

        Assertions:
            - The `initialize` method raises a RedisError with the correct message.
            - The Redis connection is not initialized.

        Raises:
            - AssertionError: If the RedisError is not raised or the connection is initialized.
        """
        with patch('redis.asyncio.Redis.from_url', side_effect=redis.asyncio.RedisError("Failed to initialize Redis connection pool.")) as mock_from_url:
            event_store = RedisEventStoreAdapter('redis://test')
            with pytest.raises(redis.asyncio.RedisError, match="Failed to initialize Redis connection pool."):
                await event_store.initialize()
            mock_from_url.assert_called_once_with('redis://test')
            assert event_store.redis is None

    async def test_is_processed_returns_true_when_event_exists(self):
        """
        Test that the `is_processed` method returns True when the event exists.

        Assertions:
            - The `is_processed` method returns True when the event ID exists in Redis.

        Raises:
            - AssertionError: If the method does not return True.
        """
        event_store = RedisEventStoreAdapter('redis://test')
        mock_redis = AsyncMock()
        event_store.redis = mock_redis
        mock_redis.exists.return_value = 1

        result = await event_store.is_processed('test_event')
        assert result is True
        mock_redis.exists.assert_awaited_once_with('test_event')

    async def test_is_processed_returns_false_when_event_does_not_exist(self):
        """
        Test that the `is_processed` method returns False when the event does not exist.

        Assertions:
            - The `is_processed` method returns False when the event ID does not exist in Redis.

        Raises:
            - AssertionError: If the method does not return False.
        """
        event_store = RedisEventStoreAdapter('redis://test')
        mock_redis = AsyncMock()
        event_store.redis = mock_redis
        mock_redis.exists.return_value = 0

        result = await event_store.is_processed('test_event')
        assert result is False
        mock_redis.exists.assert_awaited_once_with('test_event')

    async def test_is_processed_raises_redis_error(self):
        """
        Test that the `is_processed` method raises a RedisError when querying Redis fails.

        Assertions:
            - The `is_processed` method raises a RedisError with the correct message.

        Raises:
            - AssertionError: If the RedisError is not raised.
        """
        event_store = RedisEventStoreAdapter('redis://test')
        mock_redis = AsyncMock()
        event_store.redis = mock_redis
        mock_redis.exists.side_effect = redis.asyncio.RedisError("Error checking if event is processed.")

        with pytest.raises(redis.asyncio.RedisError, match="Error checking if event is processed."):
            await event_store.is_processed('test_event')

    async def test_mark_as_processed_sets_event_with_expiration(self):
        """
        Test that the `mark_as_processed` method sets the event with an expiration.

        Assertions:
            - The `mark_as_processed` method sets the event ID in Redis with a 30-day expiration.

        Raises:
            - AssertionError: If the event is not set with the correct expiration.
        """
        event_store = RedisEventStoreAdapter('redis://test')
        mock_redis = AsyncMock()
        event_store.redis = mock_redis

        await event_store.mark_as_processed('test_event')
        mock_redis.set.assert_awaited_once_with('test_event', 'processed', ex=2592000)

    async def test_mark_as_processed_raises_redis_error(self):
        """
        Test that the `mark_as_processed` method raises a RedisError when setting the event fails.

        Assertions:
            - The `mark_as_processed` method raises a RedisError with the correct message.

        Raises:
            - AssertionError: If the RedisError is not raised.
        """
        event_store = RedisEventStoreAdapter('redis://test')
        mock_redis = AsyncMock()
        event_store.redis = mock_redis
        mock_redis.set.side_effect = redis.asyncio.RedisError("Error marking event as processed.")

        with pytest.raises(redis.asyncio.RedisError, match="Error marking event as processed."):
            await event_store.mark_as_processed('test_event')

    async def test_close_closes_redis_connection(self):
        """
        Test that the `close` method closes the Redis connection.

        Assertions:
            - The `close` method closes the Redis connection.

        Raises:
            - AssertionError: If the connection is not closed.
        """
        event_store = RedisEventStoreAdapter('redis://test')
        mock_redis = AsyncMock()
        event_store.redis = mock_redis

        await event_store.close()
        mock_redis.close.assert_awaited_once()

    async def test_close_raises_redis_error(self):
        """
        Test that the `close` method raises a RedisError when closing the connection fails.

        Assertions:
            - The `close` method raises a RedisError with the correct message.

        Raises:
            - AssertionError: If the RedisError is not raised.
        """
        event_store = RedisEventStoreAdapter('redis://test')
        mock_redis = AsyncMock()
        event_store.redis = mock_redis
        mock_redis.close.side_effect = redis.asyncio.RedisError("Error closing Redis connection.")

        with pytest.raises(redis.asyncio.RedisError, match="Error closing Redis connection."):
            await event_store.close()
