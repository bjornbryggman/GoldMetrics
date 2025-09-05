# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides an asynchronous`AbstractEventBus` adapter using Redis and RabbitMQ.

This module includes:
- `RedisEventStore`: Manages event processing state using Redis to track processed events.
- `RabbitMQEventBusAdapter`: Asynchronous message broker using RabbitMQ for publishing and subscribing to events.
"""

import json
from collections.abc import Callable, Coroutine
from typing import Any, Self

import aio_pika
import redis.asyncio
from structlog import stdlib

from backend.app.application import ports

log = stdlib.get_logger(__name__)

# ======================================= #
#               Event Store               #
# ======================================= #


class RedisEventStoreAdapter(ports.AbstractEventStore):
    """
    Event processing state manager using Redis.

    This class tracks processed events, ensuring idempotency by preventing
    duplicate processing of the same event.

    Attributes:
        - redis_url: The URL for connecting to Redis.
        - redis: The Redis connection pool.

    Methods:
        - initialize: Initializes the Redis connection pool.
        - is_processed: Checks if an event has already been processed.
        - mark_as_processed: Marks an event as processed.
        - close: Closes the Redis connection gracefully.
    """

    def __init__(self, redis_url: str) -> None:
        """
        Initialize the EventStoreRedis.

        Args:
            - redis_url: The URL for connecting to Redis.
        """
        self.redis_url = redis_url
        self.redis = None

    async def initialize(self) -> None:
        """
        Initialize the Redis connection pool.

        Raises:
            - redis.asyncio.RedisError: If an error occurs while connecting to Redis.
        """
        if not self.redis:
            try:
                self.redis = await redis.asyncio.Redis.from_url(self.redis_url)
                await log.adebug("Redis connection pool initialized.")
            except redis.asyncio.RedisError:
                await log.aexception("Failed to initialize Redis connection pool.")
                raise

    async def is_processed(self, event_id: str) -> bool:
        """
        Check if an event has already been processed.

        Args:
            - event_id: The unique identifier of the event.

        Returns:
            - bool: True if the event has been processed, False otherwise.

        Raises:
            - redis.asyncio.RedisError: If an error occurs while querying Redis.
        """
        await self.initialize()
        try:
            # Check if the event ID exists in Redis
            exists = await self.redis.exists(event_id)
            await log.adebug("Checked if event '%s' is processed: %s", event_id, exists == 1)
        except redis.asyncio.RedisError:
            await log.aexception("Error checking if event '%s' is processed.", event_id)
            raise
        else:
            return exists == 1

    async def mark_as_processed(self, event_id: str) -> None:
        """
        Mark an event as processed.

        Args:
            - event_id: The unique identifier of the event.

        Raises:
            - redis.asyncio.RedisError: If an error occurs while updating Redis.
        """
        await self.initialize()
        try:
            # Store event ID with 30-day expiration
            await self.redis.set(event_id, "processed", ex=2592000)
            await log.adebug("Marked event '%s' as processed.", event_id)
        except redis.asyncio.RedisError:
            await log.aexception("Error marking event '%s' as processed.", event_id)
            raise

    async def close(self) -> None:
        """
        Close the Redis connection gracefully.

        Raises:
            - redis.asyncio.RedisError: If an error occurs while closing the connection.
        """
        if self.redis:
            try:
                await self.redis.close()
                await log.adebug("Redis connection closed.")
            except redis.asyncio.RedisError:
                await log.aexception("Error closing Redis connection.")
                raise


# ===================================== #
#               Event Bus               #
# ===================================== #


class RabbitMQEventBusAdapter(ports.AbstractEventBus):
    """
    Asynchronous event bus using RabbitMQ.

    This class provides methods for publishing and subscribing to events, ensuring
    reliable message delivery and idempotency through the use of an event store.

    Attributes:
        - rabbitmq_url: The URL for connecting to the message broker.
        - exchange_name: The name of the RabbitMQ exchange.
        - connection: The RabbitMQ connection.
        - channel: The RabbitMQ channel.
        - exchange: The RabbitMQ exchange.
        - subscriptions: A list of active subscriptions.
        - event_store: The event store for tracking processed events.

    Methods:
        - connect: Establishes a connection to RabbitMQ.
        - publish: Publishes an event to the exchange.
        - subscribe: Subscribes to an event and processes it with the provided handler.
        - close: Closes the RabbitMQ connection gracefully.
        - __aenter__: Enters the context manager and connects to RabbitMQ.
        - __aexit__: Exits the context manager and closes the connection.
    """

    def __init__(
        self, rabbitmq_url: str, event_store: ports.AbstractEventStore, exchange_name: str = "events_exchange"
    ) -> None:
        """
        Initialize the EventBusRabbitMQ.

        Args:
            - rabbitmq_url: The URL for connecting to the message broker.
            - event_store: The event store for tracking processed events.
            - exchange_name: The name of the RabbitMQ exchange.
        """
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.RobustChannel | None = None
        self.exchange: aio_pika.Exchange | None = None
        self.subscriptions: list[tuple[str, Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]] = []
        self.event_store = event_store

    async def connect(self) -> None:
        """
        Establish a connection to RabbitMQ.

        Raises:
            - aio_pika.exceptions.AMQPError: If an error occurs while connecting to RabbitMQ.
        """
        if not self.connection or self.connection.is_closed:
            try:
                # Establish a robust connection to RabbitMQ
                self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
                await log.adebug("Connected to RabbitMQ.")
            except aio_pika.exceptions.AMQPError:
                await log.aexception("Failed to connect to RabbitMQ.")
                raise

        if not self.channel or self.channel.is_closed:
            # Open a new channel
            self.channel = await self.connection.channel()
            await log.adebug("RabbitMQ Channel opened")

        if not self.exchange:
            # Declare the exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
            )
            await log.adebug("RabbitMQ Exchange '%s' declared", self.exchange_name)

    async def publish(self, event: ports.Event) -> None:
        """
        Publish an event to the exchange.

        Args:
            - event: The event to be published, must inherit from 'Event'.

        Raises:
            - aio_pika.exceptions.AMQPError: If an error occurs while publishing the event.
        """
        await self.connect()

        # Get the event type and data
        event_name = event.event_type
        data = event.__dict__

        # Create a message with the event data
        message = aio_pika.Message(
            body=json.dumps(data).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        )

        try:
            # Publish the message to the exchange
            await self.exchange.publish(message, routing_key=event_name)
            await log.ainfo("Published event '%s' with data: %s", event_name, data)
        except aio_pika.exceptions.AMQPError:
            await log.aexception("Failed to publish event '%s'.", event_name)
            raise

    async def subscribe(self, event_name: str, handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        """
        Subscribe to an event and process it with the provided handler.

        Args:
            - event_name: The name of the event to subscribe to.
            - handler: An asynchronous callable that processes the event data.

        Raises:
            - aio_pika.exceptions.AMQPError: If an error occurs while subscribing to the event.
        """
        await self.connect()

        # Declare a queue for the event
        queue = await self.channel.declare_queue(name=f"{event_name}_queue", durable=True, auto_delete=False)

        # Bind the queue to the exchange with the specified routing key
        await queue.bind(self.exchange, routing_key=event_name)
        await log.ainfo(
            "Queue '%s' bound to exchange '%s' with routing key '%s'.", queue.name, self.exchange_name, event_name
        )

        async def on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process():
                try:
                    # Parse the message body
                    data = json.loads(message.body.decode())
                    event_id = data.get("event_id")

                    # Check for event_id and handle duplicate events
                    if not event_id:
                        await log.aerror("Received event without event_id. Rejecting message.")
                        await message.reject(requeue=False)
                        return
                    if await self.event_store.is_processed(event_id):
                        await log.ainfo("Duplicate event '%s' received. Skipping processing.", event_id)
                        return

                    # Process the event with the provided handler
                    await handler(data)
                    await self.event_store.mark_as_processed(event_id)
                    await log.ainfo("Event '%s' processed and marked as processed.", event_id)

                except json.JSONDecodeError:
                    await log.aexception("Invalid JSON in message.")
                    await message.reject(requeue=False)
                    raise
                except Exception:
                    await log.aexception("Error processing message.")
                    await message.reject(requeue=True)

        try:
            # Start consuming messages from the queue
            await queue.consume(on_message)
            self.subscriptions.append((event_name, handler))
        except aio_pika.exceptions.AMQPError:
            await log.aexception("Failed to subscribe to event '%s'.", event_name)
            raise

    async def close(self) -> None:
        """
        Close the RabbitMQ connection gracefully.

        Raises:
            - aio_pika.exceptions.AMQPError: If an error occurs while closing the connection.
        """
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
            await log.ainfo("RabbitMQ Channel closed.")

        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            await log.ainfo("RabbitMQ Connection closed.")

    async def __aenter__(self) -> Self:
        """
        Enter the context manager, ensure the event store is running and connect to RabbitMQ.

        Returns:
            - Self: The instance of the EventBusRabbitMQ.
        """
        await self.event_store.initialize()
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager and close the RabbitMQ connection.

        Args:
            - exc_type: The type of the exception, if any.
            - exc_val: The exception instance, if any.
            - exc_tb: The traceback, if any.
        """
        await self.close()
