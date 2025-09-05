# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides domain models for financial instruments and related data.

This module includes:
- `Exchange`: Domain entity representing a financial exchange.
- `Ticker`: Domain entity representing a financial ticker..
- `HistoricalData`: Domain entity representing historical data for a financial ticker.
- `TechnicalData`: Domain entity representing technical data for a financial ticker.
- `FinancialInstrumentAR`: Aggregate root for managing financial instrument data and formatting methods.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

# =================================== #
#               Entities              #
# =================================== #


@dataclass
class Exchange:
    """
    Represents a financial exchange.

    Attributes:
        - name: The name of the exchange.
        - code: The code of the exchange.
        - operatingmic: The operating MIC of the exchange.
        - country: The country where the exchange is located.
        - currency: The currency used by the exchange.
        - countryiso2: The ISO 2-letter country code.
        - countryiso3: The ISO 3-letter country code.
        - created_at: The timestamp when the exchange was created.
        - modified_at: The timestamp when the exchange was last modified.
    """

    name: str
    code: str
    operatingmic: str
    country: str
    currency: str
    countryiso2: str
    countryiso3: str

    created_at: datetime = field(default=None)
    modified_at: datetime = field(default=None)


@dataclass
class Ticker:
    """
    Represents a financial ticker.

    Attributes:
        - code: The code of the ticker.
        - name: The name of the ticker.
        - country: The country where the ticker is listed.
        - exchange: The exchange code where the ticker is listed.
        - currency: The currency of the ticker.
        - type: The type of the ticker (e.g., stock, ETF).
        - created_at: The timestamp when the ticker was created.
        - modified_at: The timestamp when the ticker was last modified.
    """

    code: str
    name: str
    country: str
    exchange: str
    currency: str
    type: str

    created_at: datetime = field(default=None)
    modified_at: datetime = field(default=None)


@dataclass
class HistoricalData:
    """
    Represents historical data for a financial ticker.

    Attributes:
        - id: The unique identifier for the historical data entry.
        - code: The code of the ticker.
        - date: The date of the historical data.
        - open: The opening price.
        - high: The highest price.
        - low: The lowest price.
        - close: The closing price.
        - adjusted_close: The adjusted closing price.
        - volume: The trading volume.
        - created_at: The timestamp when the historical data was created.
        - modified_at: The timestamp when the historical data was last modified.
    """

    code: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int

    created_at: datetime = field(default=None)
    modified_at: datetime = field(default=None)


@dataclass
class TechnicalData:
    """
    Represents technical data for a financial ticker.

    Attributes:
        - code: The code of the ticker.
        - MarketCapitalization: The market capitalization of the ticker.
        - Beta: The beta value of the ticker.
        - ema_50d: The 50-day exponential moving average.
        - ema_200d: The 200-day exponential moving average.
        - hi_250d: The 250-day high.
        - low_250d: The 250-day low.
        - prev_close: The previous closing price.
        - change: The price change.
        - change_p: The percentage price change.
        - avgvol_14d: The 14-day average trading volume.
        - avgvol_50d: The 50-day average trading volume.
        - avgvol_200d: The 200-day average trading volume.
        - created_at: The timestamp when the technical data was created.
        - modified_at: The timestamp when the technical data was last modified.
    """

    code: str
    MarketCapitalization: int
    Beta: float
    ema_50d: float
    ema_200d: float
    hi_250d: float
    low_250d: float
    prev_close: float
    change: float
    change_p: float
    avgvol_14d: float
    avgvol_50d: float
    avgvol_200d: float

    created_at: datetime = field(default=None)
    modified_at: datetime = field(default=None)


# ===================================== #
#               Aggregates              #
# ===================================== #


@dataclass
class FinancialInstrumentAR:
    """
    Aggregate root for managing financial instrument data.

    This class provides methods for formatting and filtering financial instrument data,
    including tickers, exchanges, historical data, and technical data.

    Methods:
        - format_ticker: Formats raw ticker data into a `Ticker` object.
        - format_exchange: Formats raw exchange data into an `Exchange` object.
        - format_historical_data: Formats raw historical data into a list of `HistoricalData` objects.
        - format_technical_data: Formats raw technical data into a `TechnicalData` object.
        - filter_end_of_day_data: Filters end-of-day data into historical and technical data components.
    """

    @staticmethod
    def format_ticker(ticker: dict) -> Ticker:
        """
        Format raw ticker data into a `Ticker` object.

        Args:
            - ticker: The raw ticker data.

        Returns:
            - Ticker: The formatted ticker object.
        """
        return Ticker(**ticker)

    @staticmethod
    def format_exchange(exchange: dict) -> Exchange:
        """
        Format raw exchange data into an `Exchange` object.

        Args:
            - exchange: The raw exchange data.

        Returns:
            - Exchange: The formatted exchange object.
        """
        return Exchange(**exchange)

    @staticmethod
    def format_historical_data(historical_data: dict) -> HistoricalData:
        """
        Format raw historical data into an `HistoricalData` object.

        Args:
            - historical_data: The raw historical data.

        Returns:
            - list[HistoricalData]: The formatted historical data objects.
        """
        date = historical_data["date"]
        if isinstance(date, datetime):
            tz_aware_date = date.replace(tzinfo=UTC)
        else:
            converted_date = datetime.strptime(date, "%Y-%m-%d")
            tz_aware_date = converted_date.replace(tzinfo=UTC)
        historical_data["date"] = tz_aware_date
        return HistoricalData(**historical_data)

    @staticmethod
    def format_technical_data(technical_data: dict) -> TechnicalData:
        """
        Format raw technical data into a `TechnicalData` object.

        Args:
            - technical_data: The raw technical data.

        Returns:
            - TechnicalData: The formatted technical data object.
        """
        return TechnicalData(**technical_data)

    @staticmethod
    def filter_end_of_day_data(end_of_day_data: dict) -> tuple[dict, dict]:
        """
        Filter end-of-day data into historical and technical data components.

        Args:
            - end_of_day_data: The raw end-of-day data.

        Returns:
            - tuple[HistoricalData, TechnicalData]: The filtered historical and technical data.
        """
        historical_data_keys = {
            "code",
            "date",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
        }
        technical_data_keys = {
            "code",
            "MarketCapitalization",
            "Beta",
            "ema_50d",
            "ema_200d",
            "hi_250d",
            "low_250d",
            "prev_close",
            "change",
            "change_p",
            "avgvol_14d",
            "avgvol_50d",
            "avgvol_200d",
        }

        # Filter historical data
        historical_data = {
            key: end_of_day_data.get(key) for key in historical_data_keys
        }

        # Filter technical data
        technical_data = {key: end_of_day_data.get(key) for key in technical_data_keys}

        return historical_data, technical_data
