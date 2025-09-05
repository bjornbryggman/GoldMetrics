# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides an asynchronous `AbstractUnitOfWork` adapter using SQLAlchemy.

This module includes:
- `SQLAlchemyUnitOfWorkAdapter`: Manages asynchronous database transactions using SQLAlchemy's AsyncSession.
"""

from typing import Self

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog import stdlib

from backend.app.application import ports
from backend.app.infrastructure.adapters import repository

log = stdlib.get_logger(__name__)

# ======================================== #
#               Unit of Work               #
# ======================================== #


class SQLAlchemyUnitOfWorkAdapter(ports.AbstractUnitOfWork):
    """
    Asynchronous Unit of Work using SQLAlchemy.

    This class manages database transactions using SQLAlchemy's AsyncSession,
    ensuring that operations are atomic and consistent. It also provides access
    to the `SQLAlchemyFIARRepositoryAdapter` for managing financial instrument data.

    Attributes:
        - session_factory: The async session factory for creating database sessions.
        - financial_instrument: The repository for managing financial instrument data.

    Methods:
        - commit: Commits the current database session.
        - rollback: Rolls back the current database session.
        - __aenter__: Enters the context manager and initializes the session and repository.
        - __aexit__: Exits the context manager and closes the session.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """
        Initialize the SQLAlchemyUnitOfWork.

        Args:
            - session_factory: The async session factory for creating database sessions.
        """
        self.session_factory = session_factory

    async def commit(self) -> None:
        """
        Commit the current database session.

        Raises:
            - SQLAlchemyError: If an error occurs during the commit operation.
        """
        try:
            await self.session.commit()
            await log.adebug("Committed database session.")
        except SQLAlchemyError:
            await log.aexception("Error committing database session.")
            raise

    async def rollback(self) -> None:
        """
        Roll back the current database session.

        Raises:
            - SQLAlchemyError: If an error occurs during the rollback operation.
        """
        try:
            await self.session.rollback()
            await log.adebug("Rolled back database session.")
        except SQLAlchemyError:
            await log.aexception("Error rolling back database session.")
            raise

    async def __aenter__(self) -> Self:
        """
        Enter the context manager and initialize the session and repository.

        Returns:
            - Self: The instance of the Unit of Work.

        Raises:
            - SQLAlchemyError: If an error occurs while initializing the database session.
        """
        try:
            # Initialize the database session
            self.session = self.session_factory()
            await self.session.__aenter__()

            # Initialize the repository for managing financial instrument data
            self.financial_instrument = repository.SQLAlchemyFIARRepositoryAdapter(self.session)

            await log.adebug("Database session and repository initialized.")
        except SQLAlchemyError:
            await log.aexception("Error initializing database session.")
            raise
        else:
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager and close the session.

        Args:
            - exc_type: The type of the exception, if any.
            - exc_val: The exception instance, if any.
            - exc_tb: The traceback, if any.

        Raises:
            - SQLAlchemyError: If an error occurs when closing the database session.
        """
        try:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)
            await log.adebug("Database session closed.")
        except SQLAlchemyError:
            await log.aexception("Error closing database session.")
            raise
