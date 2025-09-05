# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"Something."

from structlog import stdlib

from backend.app.application.services import EODHDService
from backend.app.infrastructure.adapters.api import EODHDAPIClient

from backend.tests.fake_data import raw_fi_test_data

log = stdlib.get_logger(__name__)

# ================================= #
#               EODHD               #
# ================================= #


class FakeEODHDAPIClient(EODHDAPIClient):
    def __init__(self) -> None:
        """
        Initialize the EODHDAPIClient.
        """
        self.unformatted_fi_test_data = raw_fi_test_data()

    async def get_exchanges(self) -> list[dict]:
        """
        Fetch the list of available exchanges.

        Returns:
            - list[dict]: A list of available exchanges.
        """
        list_of_test_exchanges = []
        list_of_test_exchanges.append(self.unformatted_fi_test_data.test_exchange_data)
        return list_of_test_exchanges

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
        """
        if delisted:
            return []

        list_of_test_tickers = []
        list_of_test_tickers.append(self.unformatted_fi_test_data.test_ticker_data)
        return list_of_test_tickers

    async def get_historical_data(self, ticker_code: str) -> list[dict]:
        """
        Fetch historical data for a specific ticker.

        Args:
            - ticker_code: The code of the ticker to fetch historical data for.

        Returns:
            - list[dict]: A list of historical data for the specified ticker.
        """
        return self.unformatted_fi_test_data.test_historical_data_list

    async def get_eod_bulk_data(self, exchange_code: str) -> dict:
        """
        Fetch bulk end-of-day data for a specific exchange.

        Args:
            - exchange_code: The code of the exchange to fetch bulk end-of-day data for.

        Returns:
            - list[dict]: A list of bulk end-of-day data for the specified exchange.
        """
        list_of_test_eod_bulk_data = []
        list_of_test_eod_bulk_data.append(
            self.unformatted_fi_test_data.test_eod_bulk_data
        )
        return list_of_test_eod_bulk_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def test_eodhd_service(real_dependencies) -> None:
    """
    Handle the `TestUpdateFinancialInstruments` event.

    This method initiates a simulated scan of financial instruments using the `EODHDService`.

    Args:
        - message: The `TestUpdateFinancialInstruments` event.

    Raises:
        - Exception: If an error occurs during the handling of the event.
    """
    unit_of_work = real_dependencies.unit_of_work
    event_bus = real_dependencies.event_bus
    api_client = FakeEODHDAPIClient()

    await EODHDService(
        unit_of_work=unit_of_work,
        event_bus=event_bus,
        api_client=api_client,
    ).update_financial_instruments([])

    async with unit_of_work() as uow_1:
        fetched_exchange = await uow_1.financial_instrument.get_exchange("NYSE")
        fetched_ticker = await uow_1.financial_instrument.get_ticker("ABC")
        fetched_historical_data = await uow_1.financial_instrument.get_historical_data(
            "ABC"
        )
        fetched_technical_data = await uow_1.financial_instrument.get_technical_data(
            "ABC"
        )
        assert fetched_exchange.code == "NYSE"
        assert fetched_ticker.code == "ABC"
        assert len(fetched_historical_data) == 4
        assert fetched_technical_data.code == "ABC"
