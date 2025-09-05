# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides an asynchronous `AbstractFinancialInstrumentRepository` adapter using SQLAlchemy.

This module includes:
- `SQLAlchemyFIARRepositoryAdapter`: Manages financial instrument data, including tickers,
    exchanges, historical data, and technical data, using SQLAlchemy for database interactions.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import stdlib

from backend.app.application import ports
from backend.app.domain import models

log = stdlib.get_logger(__name__)

# ====================================== #
#               Repository               #
# ====================================== #


class SQLAlchemyFIARRepositoryAdapter(ports.AbstractFIARRepository):
    """
    Asynchronous repository for the FinancialInstrument aggregate root using SQLAlchemy.

    This class implements the `AbstractFinancialInstrumentRepository` interface by providing
    methods for querying and managing financial instrument data, including tickers, exchanges,
    historical data, and technical data, using SQLAlchemy.

    Attributes:
        - session: The SQLAlchemy `AsyncSession` for database interactions.

    Methods:
        - get_ticker: Retrieves tickers, either specifically or all at once.
        - get_exchange: Retrieves exchanges, either specifically or all at once.
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

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the SQLFinancialInstrumentRepository.

        Args:
            - session: The SQLAlchemy `AsyncSession` for database interactions.
        """
        self.session = session

    async def get_ticker(self, code: str | None, all: bool = False) -> models.Ticker | None:
        """
        Retrieve tickers, either specifically or all at once.

        Args:
            - code | None: The specific code of the ticker to retrieve, or None.
            - all: Whether or not to fetch all available tickers. Defaults to False.

        Returns:
            - model.Ticker | None: The retrieved ticker, or None if not found.

        Raises:
            - SQLAlchemyError: If an error occurs during the database query.
        """
        try:
            if not code or all:
                log.aerror("Invalid parameters.")
            if code:
                query = select(models.Ticker).where(models.Ticker.code == code)
                result = await self.session.execute(query)
                return result.scalar_one_or_none()
            if all:
                query = select(models.Ticker)
                result = await self.session.execute(query)
                return result.scalars().all()

        except SQLAlchemyError:
            await log.aexception("Error retrieving ticker: %s", code)
            raise

    async def get_exchange(self, code: str | None, all: bool = False) -> models.Exchange | None:
        """
        Retrieve exchanges, either specifically or all at once.

        Args:
            - code | None: The code of the exchange to retrieve, or None.
            - all: Whether or not to fetch all available exchanges. Defaults to False.

        Returns:
            - model.Exchange | None: The retrieved exchange, or None if not found.

        Raises:
            - SQLAlchemyError: If an error occurs during the database query.
        """
        try:
            if not code or all:
                log.aerror("Invalid parameters.")
            if code:
                query = select(models.Exchange).where(models.Exchange.code == code)
                result = await self.session.execute(query)
                return result.scalar_one_or_none()
            if all:
                query = select(models.Exchange)
                result = await self.session.execute(query)
                return result.scalars().all()

        except SQLAlchemyError:
            await log.aexception("Error retrieving exchange: %s", code)
            raise


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

        Raises:
            - SQLAlchemyError: If an error occurs during the database query.
        """
        try:
            query = select(models.HistoricalData).where(models.HistoricalData.code == code)
            if start_date:
                converted_start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=UTC)
                query = query.where(converted_start_date <= models.HistoricalData.date)
            if end_date:
                converted_end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=UTC)
                query = query.where(converted_end_date >= models.HistoricalData.date)
            if start_date and end_date:
                converted_start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=UTC)
                converted_end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=UTC)
                query = query.where(converted_start_date <= models.HistoricalData.date >= converted_end_date)
            result = await self.session.execute(query)
        except SQLAlchemyError:
            await log.aexception("Error retrieving historical data for ticker: %s", code)
            raise
        else:
            return result.scalars().all()

    async def get_technical_data(self, code: str) -> models.TechnicalData | None:
        """
        Retrieve technical data for a ticker.

        Args:
            - code: The code of the ticker to retrieve technical data for.

        Returns:
            - model.TechnicalData | None: The retrieved technical data, or None if not found.

        Raises:
            - SQLAlchemyError: If an error occurs during the database query.
        """
        try:
            query = select(models.TechnicalData).where(models.TechnicalData.code == code)
            result = await self.session.execute(query)
        except SQLAlchemyError:
            await log.aexception("Error retrieving technical data for ticker: %s", code)
            raise
        else:
            return result.scalar_one_or_none()

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

        Raises:
            - SQLAlchemyError: If an error occurs during the database query.
        """
        try:
            ticker_data = await self.get_ticker(code)
            technical_data = await self.get_technical_data(code)
            historical_data = await self.get_historical_data(code, start_date, end_date)
        except SQLAlchemyError:
            await log.aexception("Error retrieving ticker with technical and historical data: %s", code)
            raise
        else:
            return ticker_data, technical_data, historical_data

    async def update_technical_data(self, technical_data: models.TechnicalData) -> None:
        """
        Update technical data for a ticker.

        Args:
            - technical_data: The technical data to update.

        Raises:
            - SQLAlchemyError: If an error occurs during the database update.
        """
        try:
            existing_data = await self.get_technical_data(technical_data.code)
            if existing_data is None:
                await log.aexception("Technical data with code '%s' not found.", technical_data.code)
                raise ValueError

            for key, value in technical_data.__dict__.items():
                if not key.startswith("_"):
                    setattr(existing_data, key, value)
        except SQLAlchemyError:
            await log.aexception("Error updating technical data for ticker: %s", technical_data.code)
            raise

    async def add_ticker(self, ticker: models.Ticker) -> None:
        """
        Add a new ticker to the repository.

        Args:
            - ticker: The ticker to add.

        Raises:
            - SQLAlchemyError: If an error occurs during the database operation.
        """
        try:
            self.session.add(ticker)
        except SQLAlchemyError:
            await log.aexception("Error adding ticker: %s", ticker.code)
            raise

    async def add_exchange(self, exchange: models.Exchange) -> None:
        """
        Add a new exchange to the repository.

        Args:
            - exchange: The exchange to add.

        Raises:
            - SQLAlchemyError: If an error occurs during the database operation.
        """
        try:
            self.session.add(exchange)
        except SQLAlchemyError:
            await log.aexception("Error adding exchange: %s", exchange.code)
            raise

    async def add_historical_data(self, historical_data: models.HistoricalData) -> None:
        """
        Add historical data for a ticker.

        Args:
            - historical_data: The historical data to add.

        Raises:
            - SQLAlchemyError: If an error occurs during the database operation.
        """
        try:
            self.session.add(historical_data)
        except SQLAlchemyError:
            await log.aexception("Error adding historical data for ticker: %s", historical_data.code)
            raise

    async def add_historical_data_bulk(self, historical_data_list: list[models.HistoricalData]) -> None:
        """
        Add multiple historical data entries in bulk.

        Args:
            - historical_data_list: The list of historical data entries to add.

        Raises:
            - SQLAlchemyError: If an error occurs during the database operation.
        """
        try:
            self.session.add_all(historical_data_list)
        except SQLAlchemyError:
            await log.aexception("Error adding historical data in bulk.")
            raise

    async def add_technical_data(self, technical_data: models.TechnicalData) -> None:
        """
        Add technical data for a ticker.

        Args:
            - technical_data: The technical data to add.

        Raises:
            - SQLAlchemyError: If an error occurs during the database operation.
        """
        try:
            self.session.add(technical_data)
        except SQLAlchemyError:
            await log.aexception("Error adding technical data for ticker: %s", technical_data.code)
            raise
