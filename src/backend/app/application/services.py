# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides services of various kinds.

This module includes:
- `EODHDService`: Service for updating financial instruments using the EOD Historical Data API.
- `RabbitMQService`: Service for managing RabbitMQ message broker operations.
- `JobSchedulingService`: Service for scheduling periodic tasks.
"""

import asyncio
from importlib import metadata
from typing import Self

import polars as pl
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from structlog import stdlib

from backend.app.application.events import Notification, UpdateFinancialInstruments
from backend.app.application.ports import AbstractEventBus, AbstractEventHandler, AbstractUnitOfWork
from backend.app.domain import models
from backend.app.infrastructure.adapters.api import EODHDAPIClient

log = stdlib.get_logger(__name__)

# =============================================== #
#               EOD Historical Data               #
# =============================================== #


class EODHDService:
    """
    Service for updating financial instruments using the EOD Historical Data API.

    This service is responsible for fetching and processing financial data from the EOD Historical
    Data API, including exchanges, tickers, historical data, and technical data. It also publishes
    a notification event to notify other components when the update process is complete.

    Attributes:
        - unit_of_work: The Unit of Work for managing database transactions.
        - event_bus: The event bus for publishing notifications.
        - api_client: Shared EODHD-specific API client with explicit rate limiting.

    Methods:
        - update_financial_instruments: Entrypoint for updating financial instruments.
        - scan_exchanges: Scans and processes available exchanges.
        - scan_tickers: Scans and processes tickers for a given exchange.
        - scan_end_of_day_data: Scans and processes end-of-day data for a given exchange.
    """

    def __init__(
        self, unit_of_work: AbstractUnitOfWork, event_bus: AbstractEventBus, api_client: EODHDAPIClient
    ) -> None:
        """
        Initialize the EODHDService.

        Args:
            - unit_of_work: The Unit of Work for managing database transactions.
            - event_bus: The event bus for publishing notifications.
            - api_client: Shared EODHD-specific API client with explicit rate limiting.
        """
        self.unit_of_work = unit_of_work
        self.event_bus = event_bus
        self.api_client = api_client

    async def update_financial_instruments(self, filters: list[str] | None = None) -> None:
        """
        Entrypoint for updating financial instruments.

        Args:
            - filters: List of exchange codes to query if specified, otherwise None.

        Raises:
            - Exception: If an error occurs during the update process.
        """
        try:
            await log.adebug("Requesting list of available exchanges...")
            ticker_processing_tasks = []
            end_of_day_processing_tasks = []

            # Get list of exchange codes
            if filters:
                list_of_exchange_codes = filters
            else:
                list_of_exchange_codes = await self.scan_exchanges()

            # Create tasks for scanning tickers and end-of-day data
            ticker_processing_tasks.extend(self.scan_tickers(exchange) for exchange in list_of_exchange_codes)
            end_of_day_processing_tasks.extend(
                self.scan_end_of_day_data(exchange) for exchange in list_of_exchange_codes
            )

            # Execute tasks concurrently
            await asyncio.gather(*ticker_processing_tasks)
            await asyncio.gather(*end_of_day_processing_tasks)

            # Publish notification event
            async with self.event_bus() as event_bus:
                event = Notification(text="Fetched new data for financial instruments.")
                await event_bus.publish(event)
        except Exception:
            await log.aexception("Error updating financial instruments.")
            raise

    async def scan_exchanges(self) -> list[str]:
        """
        Scan and process available exchanges.

        Returns:
            - list[str]: List of exchange codes.

        Raises:
            - Exception: If an error occurs during the scanning.
        """
        try:
            await log.adebug("Requesting list of available exchanges...")
            list_of_exchange_codes = []
            processing_tasks = []

            # Fetch list of exchanges from API
            async with self.api_client as api_client:
                list_of_exchanges = await api_client.get_exchanges()

            # Process each exchange
            for exchange in list_of_exchanges:

                async def process_exchange(exchange: dict = exchange) -> None:
                    try:
                        await log.adebug("Processing exchange: '%s'", exchange["code"])
                        async with self.unit_of_work() as uow:
                            formatted_exchange = models.FinancialInstrumentAR.format_exchange(exchange)
                            existing_exchange = await uow.financial_instrument.get_exchange(formatted_exchange.code)
                            if not existing_exchange:
                                await uow.financial_instrument.add_exchange(formatted_exchange)
                                await uow.commit()
                    except Exception:
                        await log.aexception("Error processing exchange: '%s'", exchange["code"])
                        raise

                list_of_exchange_codes.append(exchange["code"])
                processing_tasks.append(process_exchange())

            # Execute tasks concurrently
            await asyncio.gather(*processing_tasks)

        except Exception:
            await log.aexception("Error scanning for new exchanges.")
            raise
        else:
            return list_of_exchange_codes

    async def scan_tickers(self, exchange: str) -> None:
        """
        Scan and process tickers for a given exchange.

        Args:
            - exchange: The exchange code to scan.

        Raises:
            - Exception: If an error occurs during the scanning.
        """
        try:
            await log.adebug("Scanning for new tickers in exchange: '%s'", exchange)
            processing_tasks = []

            # Fetch list of tickers from API
            async with self.api_client as api_client:
                list_of_current_tickers = await api_client.get_tickers(exchange)
                list_of_delisted_tickers = await api_client.get_tickers(exchange, delisted=True)
                list_of_all_tickers = list_of_current_tickers + list_of_delisted_tickers

            # Process each ticker
            for ticker in list_of_all_tickers:

                async def process_ticker(ticker: dict = ticker) -> None:
                    try:
                        await log.adebug("Processing ticker: '%s'", ticker["code"])
                        async with self.unit_of_work() as uow:
                            if not await uow.financial_instrument.get_ticker(ticker["code"]):
                                await log.adebug("Adding financial instrument '%s' to database.", ticker["code"])
                                raw_list_of_historical_data = await api_client.get_historical_data(ticker["code"])

                                formatted_ticker = models.FinancialInstrumentAR.format_ticker(ticker)
                                formatted_historical_data = []
                                for date in raw_list_of_historical_data:
                                    historical_data_object = models.FinancialInstrumentAR.format_historical_data(date)
                                    formatted_historical_data.append(historical_data_object)

                                await uow.financial_instrument.add_ticker(formatted_ticker)
                                await uow.commit()
                                await uow.financial_instrument.add_historical_data_bulk(formatted_historical_data)
                                await uow.commit()
                    except Exception:
                        await log.aexception("Error processing ticker: '%s'", ticker["code"])
                        raise

                processing_tasks.append(process_ticker())

            # Execute tasks concurrently
            await asyncio.gather(*processing_tasks)
        except Exception:
            await log.aexception("Error scanning for new tickers in exchange: '%s'", exchange)
            raise

    async def scan_end_of_day_data(self, exchange: str) -> None:
        """
        Scan and process end-of-day data for a given exchange.

        Args:
            - exchange: The exchange code to scan.

        Raises:
            - Exception: If an error occurs during the scanning.
        """
        try:
            await log.adebug("Scanning for end-of-day data for exchange: '%s'", exchange)
            processing_tasks = []

            # Fetch end-of-day data from API
            async with self.api_client as api_client:
                end_of_day_data = await api_client.get_eod_bulk_data(exchange)

            # Process each end-of-day data entry
            for data in end_of_day_data:

                async def process_eod_data(data: dict = data) -> None:
                    try:
                        await log.adebug("Processing end-of-day data.")
                        raw_historical_data, raw_technical_data = models.FinancialInstrumentAR.filter_end_of_day_data(
                            data
                        )
                        formatted_historical_data = models.FinancialInstrumentAR.format_historical_data(
                            raw_historical_data
                        )
                        formatted_technical_data = models.FinancialInstrumentAR.format_technical_data(
                            raw_technical_data
                        )

                        async with self.unit_of_work() as uow:
                            await uow.financial_instrument.add_historical_data(formatted_historical_data)
                            existing = await uow.financial_instrument.get_technical_data(formatted_technical_data.code)
                            if existing:
                                await uow.financial_instrument.update_technical_data(formatted_technical_data)
                            else:
                                await uow.financial_instrument.add_technical_data(formatted_technical_data)
                            await uow.commit()
                    except Exception:
                        await log.aexception("Error processing end-of-day data.")
                        raise

                processing_tasks.append(process_eod_data())

            # Execute tasks concurrently
            await asyncio.gather(*processing_tasks)
        except Exception:
            await log.aexception("Error updating end-of-day data for exchange: '%s'", exchange)
            raise


# ================================== #
#               Events               #
# ================================== #


class RabbitMQService:
    """
    Service for managing RabbitMQ message broker operations.

    This service dynamically loads event handlers from entry points, validates
    their implementation, and subscribes them to the appropriate event types.
    It runs indefinitely until interrupted.

    Attributes:
        - event_bus: The event bus for subscribing to and handling events.

    Methods:
        - start_message_broker: Initializes the message broker and subscribes to event handlers.
    """

    def __init__(self, event_bus: AbstractEventBus) -> None:
        """
        Initialize the RabbitMQService.

        Args:
            - event_bus: The event bus for subscribing to and handling events.
        """
        self.event_bus = event_bus

    async def start_message_broker(self) -> None:
        """
        Initialize the message broker and subscribe to event handlers.

        Raises:
            - Exception: If an error occurs during the initialization or subscription process.
        """
        async with self.event_bus:
            try:
                # Load event handlers from entry points
                entry_points = metadata.entry_points().select(group="finance_tool.event_handlers")

                for entry_point in entry_points:
                    try:
                        # Load the handler class and create an instance
                        handler_class = entry_point.load()
                        handler_instance = handler_class()

                        # Validate that the handler inherits from AbstractEventHandler
                        if not isinstance(handler_instance, AbstractEventHandler):
                            await log.aerror(
                                "Handler '%s' does not inherit from 'AbstractEventHandler'.", handler_class.__name__
                            )
                            continue

                        # Get the event type and handler method
                        event_type = handler_instance.event_type
                        handler = handler_instance.handle

                        # Subscribe the handler to the event type
                        await self.event_bus.subscribe(event_type, handler)
                        await log.adebug("Subscribed to event '%s' with handler '%s'.", event_type, handler.__name__)
                    except Exception:
                        await log.aexception("Failed to load handler '%s'.", entry_point.name)
                        raise

                await log.ainfo("Application is now running.")

                # Wait for shutdown signal
                await asyncio.Event().wait()
            except Exception:
                await log.aexception("Error starting event subscriptions.")
                raise


# ======================================= #
#               Forecasting               #
# ======================================= #


class TimeSeriesForecastingService:
    def __init__(self, unit_of_work: AbstractUnitOfWork) -> Self:
        """
        Initialize the TimeSeriesForecastingService.

        Args:
            - unit_of_work: The Unit of Work for managing database transactions.
        """
        self.unit_of_work = unit_of_work

    def model_to_dict(self, model: object) -> dict:
        return {key: value for key, value in model.__dict__.items() if not key.startswith("_")}

    async def fetch_all_tickers_with_dataframes(self) -> list[tuple]:
        list_of_tuples_containing_dataframes = []

        async with self.unit_of_work() as uow:
            all_tickers = await uow.financial_instrument.get_ticker(all=True)
            for ticker in all_tickers:
                technical_data = await uow.financial_instrument.get_technical_data(ticker.code)
                technical_dict = [self.model_to_dict(technical_data)]

                historical_data_list = []
                historical_data = await uow.financial_instrument.get_historical_data(ticker.code)
                for model in historical_data:
                    historical_dict = [self.model_to_dict(model)]
                    historical_data_list.append(historical_dict)

                list_of_tuples_containing_dataframes.append((historical_data_list, technical_dict))

        return list_of_tuples_containing_dataframes

    async def create_time_series_df(self, instrument_codes: list[str]) -> pl.DataFrame:
        """
        Create a time series dataframe for a list of instrument codes.

        Args:
            - instrument_codes: The list of financial instrument codes.

        Returns:
            - pd.DataFrame: A dataframe containing the time series data.

        Raises:
            - SQLAlchemyError: If an error occurs during the database query.
            - Exception: If an error occurs during dataframe creation.
        """
        try:
            query = (
                select(
                    models.HistoricalData.code.label("unique_id"),
                    models.HistoricalData.date.label("ds"),
                    models.HistoricalData.adjusted_close.label("y"),
                )
                .where(models.HistoricalData.code.in_(instrument_codes))
                .order_by(models.HistoricalData.code, models.HistoricalData.date)
            )
            async with self.unit_of_work() as uow:
                dataframe = asyncio.to_thread(pl.read_sql, query, uow.session.connection(), parse_dates=["ds"])
        except SQLAlchemyError:
            await log.aexception("Error occurred when querying database.")
            raise
        except Exception:
            await log.aexception("Error occurred when creating time series dataframe.")
            raise
        else:
            return await dataframe

    async def prepare_data_for_analysis(self) -> list[pl.DataFrame]:
        """
        Prepare data for analysis by retrieving and formatting time series data.

        Returns:
            - list[pd.DataFrame]: A list of dataframes containing time series data for stocks and cryptocurrencies.

        Raises:
            - Exception: If an error occurs during data preparation.
        """
        try:
            stock_codes = await self.get_filtered_instruments("stock")
            crypto_codes = await self.get_filtered_instruments("crypto", beta_filter=False)

            stocks_df = await self.create_time_series_df(stock_codes)
            cryptos_df = await self.create_time_series_df(crypto_codes)

            # TimescaleDB-specific optimizations
            stocks_df = stocks_df.set_index(["unique_id", "ds"]).sort_index()
            cryptos_df = cryptos_df.set_index(["unique_id", "ds"]).sort_index()
        except Exception as error:
            log.exception("Error preparing data for analysis.", exc_info=error)
            raise
        else:
            return stocks_df, cryptos_df


# ========================================= #
#               Job Scheduler               #
# ========================================= #


class JobSchedulingService:
    """
    Service for scheduling periodic tasks using APScheduler.

    This service manages scheduled jobs, ensuring that tasks are executed at the
    specified intervals. It uses APScheduler for scheduling and managing jobs.

    Attributes:
        - event_bus: The event bus for publishing events.
        - scheduler: The APScheduler instance for managing scheduled jobs.

    Methods:
        - schedule_financial_instruments_update: Schedules a job to update financial instruments daily.
        - start_job_schedulers: Starts all scheduled jobs.
    """

    def __init__(self, event_bus: AbstractEventBus) -> None:
        """
        Initialize the JobSchedulingService.

        Args:
            - event_bus: The event bus for publishing events.
        """
        self.event_bus = event_bus
        self.scheduler = AsyncIOScheduler()
        self.scheduler.configure()

    def schedule_financial_instruments_update(self) -> None:
        """
        Schedule a job to update financial instruments daily.

        This method schedules a job using APScheduler to publish an
        `UpdateFinancialInstruments` event to the event bus every 24 hours.

        Raises:
            - Exception: If an error occurs during job scheduling.
        """
        try:
            # Define the function to publish the update event
            def publish_update() -> None:
                event = UpdateFinancialInstruments()
                self.event_bus.publish(event)

            # Schedule the job to run every 24 hours
            self.scheduler.add_job(
                func=publish_update, trigger="interval", hours=24, name="daily update of financial instruments"
            )
        except Exception:
            log.exception("Error scheduling job 'daily update of financial instruments'.")
            raise

    async def start_job_schedulers(self) -> None:
        """
        Start all scheduled jobs.

        This method starts the APScheduler, which begins executing all scheduled jobs.

        Raises:
            - Exception: If an error occurs while starting the scheduler.
        """
        try:
            # Start the scheduler if it is not already running
            if not self.scheduler.running:
                self.scheduler.start()

            # Schedule the financial instruments update job
            self.schedule_financial_instruments_update()
        except Exception:
            await log.aexception("Error starting job schedulers.")
            raise
