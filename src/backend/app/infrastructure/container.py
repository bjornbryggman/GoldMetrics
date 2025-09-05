# Copyright 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides a dependency injection container for the application.

This module includes:
- `Container`: A dependency injection container that provides instances of various
  configurations, adapters and services.
"""

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.infrastructure.adapters.api import EODHDAPIClient
from backend.app.infrastructure.adapters.event_bus import RabbitMQEventBusAdapter, RedisEventStoreAdapter
from backend.app.infrastructure.adapters.notifications import TelegramNotificationAdapter
from backend.app.infrastructure.adapters.unit_of_work import SQLAlchemyUnitOfWorkAdapter
from backend.app.infrastructure.config import AppConfig

# ========================================================== #
#               Dependency Injection Container               #
# ========================================================== #


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container for the application.

    This container provides instances of various services and adapters, including:
    - Database engine and session factory for database interactions.
    - Unit of Work for managing database transactions.
    - Event store and event bus for event-driven communication.
    - Notification adapter for sending notifications.
    - API clients for interacting with external APIs.

    Attributes:
        - wiring_config: Configuration for dependency injection wiring.
        - config: Application configuration provider.
        - database_engine: Singleton provider for the SQLAlchemy async database engine.
        - session_factory: Factory provider for the SQLAlchemy async session factory.
        - unit_of_work: Factory provider for the SQLAlchemy Unit of Work.
        - event_store: Singleton provider for the Redis event store.
        - event_bus: Singleton provider for the RabbitMQ event bus.
        - telegram_notification: Singleton provider for the Telegram notification adapter.
        - eodhd_api_client: Factory provider for the EOD Historical Data API client.
    """

    # ========================================= #
    #               Configuration               #
    # ========================================= #

    wiring_config = containers.WiringConfiguration(modules=["backend.app.presentation.endpoints"])
    config = providers.Singleton(AppConfig)

    # =============================================== #
    #               Database Management               #
    # =============================================== #

    database_engine = providers.Singleton(create_async_engine, config.provided.async_timescaledb_url)
    session_factory = providers.Factory(
        async_sessionmaker, database_engine.provided, expire_on_commit=False, class_=AsyncSession
    )  # type: async_sessionmaker[AsyncSession]
    unit_of_work = providers.Factory(SQLAlchemyUnitOfWorkAdapter, session_factory.provided)

    # ================================== #
    #               Events               #
    # ================================== #

    event_store = providers.Singleton(RedisEventStoreAdapter, redis_url=config.provided.redis_url)
    event_bus = providers.Singleton(
        RabbitMQEventBusAdapter, rabbitmq_url=config.provided.rabbitmq_url, event_store=event_store.provided
    )
    telegram_notification = providers.Singleton(
        TelegramNotificationAdapter, config.provided.telegram_bot_token, config.provided.telegram_chat_id
    )

    # ==================================== #
    #               Services               #
    # ==================================== #

    eodhd_api_client = providers.Factory(EODHDAPIClient, config.provided.eodhd_api_key, rate_limit=1000)
