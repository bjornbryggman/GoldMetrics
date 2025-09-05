from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncEngine
from sqlalchemy.orm import clear_mappers

from backend.app.infrastructure.container import Container
from backend.app.infrastructure.database.orm import (
    mapper_registry,
    start_database_mappers,
)

from backend.tests.fake_data import format_fi_test_data, raw_fi_test_data

# =============================================== #
#               Database Management               #
# =============================================== #


async def create_database_tables(engine: AsyncEngine) -> None:
    """
    Create all database tables defined in the metadata.

    Note:
    - This function is only for testing, in production Alembic
        is the one source of truth regarding database management!

    Args:
        - engine: The SQLAlchemy `AsyncEngine` for database interactions.

    Raises:
        - Exception: If an error occurs during table creation.
    """
    async with engine.begin() as conn:
        await conn.run_sync(mapper_registry.metadata.create_all)
    await engine.dispose()


async def drop_all_tables(engine: AsyncEngine) -> None:
    """
    Drop all database tables defined in the metadata.

    Note:
    - This function is only for testing, in production Alembic
        is the one source of truth regarding database management!

    Args:
        - engine: The SQLAlchemy `AsyncEngine` for database interactions.

    Raises:
        - Exception: If an error occurs during table deletion.
    """
    async with engine.begin() as conn:
        await conn.run_sync(mapper_registry.metadata.drop_all)
    await engine.dispose()


# ======================================== #
#               Dependencies               #
# ======================================== #


@dataclass
class Bootstrap:
    def __init__(self) -> None:
        self.container = Container()
        self.config = self.container.config
        self.database_engine = self.container.database_engine
        self.event_bus = self.container.event_bus
        self.event_store = self.container.event_store
        self.notification = self.container.telegram_notification
        self.session_factory = self.container.session_factory
        self.unit_of_work = self.container.unit_of_work


@pytest.fixture
async def real_dependencies():
    bootstrap = Bootstrap()
    database_engine = bootstrap.database_engine()
    await create_database_tables(database_engine)
    await start_database_mappers()

    try:
        yield bootstrap

    finally:
        clear_mappers()
        await drop_all_tables(database_engine)


@pytest.fixture
def mock_dependencies():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    session_factory = MagicMock(spec=async_sessionmaker, return_value=session)

    return type(
        "mock_dependencies",
        (),
        {"session_factory": session_factory, "session": session},
    )()


# ===================================== #
#               Test Data               #
# ===================================== #


@pytest.fixture
def unformatted_fi_test_data(real_dependencies):
    return raw_fi_test_data()


@pytest.fixture
def formatted_fi_test_data(real_dependencies):
    return format_fi_test_data()
