# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides tests for the `FinancialInstrumentAR` class.

This module includes:
- `TestFinancialInstrumentAR`: Tests for the `FinancialInstrumentAR` class.
"""

from backend.app.domain.models import FinancialInstrumentAR


class TestFinancialInstrumentAR:
    """
    Tests for the `FinancialInstrumentAR` class.

    Methods:
        - test_format_ticker_valid_data: Tests that the `format_ticker` method correctly formats ticker data.
        - test_format_exchange_valid_data: Tests that the `format_exchange` method correctly formats exchange data.
        - test_format_historical_data_valid_list: Tests that the `format_historical_data` method correctly formats historical data.
        - test_format_technical_data_valid_data: Tests that the `format_technical_data` method correctly formats technical data.
        - test_filter_end_of_day_data_with_incorrect_input: Tests that the `filter_end_of_day_data` method raises a TypeError with incorrect input.
    """

    # ====================================== #
    #               Unit Tests               #
    # ====================================== #

    def test_format_ticker_valid_data(self, unformatted_fi_test_data):
        """
        Test that the `format_ticker` method correctly formats ticker data.

        Args:
            - unformatted_fi_test_data: Fixture providing unformatted test data.

        Assertions:
            - The formatted ticker data has the correct code.
            - The type of the formatted data is "Ticker".

        Raises:
            - AssertionError: If the ticker data is not formatted correctly.
        """
        result = FinancialInstrumentAR.format_ticker(
            unformatted_fi_test_data.test_ticker_data
        )
        assert result.code == "ABC"
        assert type(result).__name__ == "Ticker"

    def test_format_exchange_valid_data(self, unformatted_fi_test_data):
        """
        Test that the `format_exchange` method correctly formats exchange data.

        Args:
            - unformatted_fi_test_data: Fixture providing unformatted test data.

        Assertions:
            - The formatted exchange data has the correct code.
            - The type of the formatted data is "Exchange".

        Raises:
            - AssertionError: If the exchange data is not formatted correctly.
        """
        result = FinancialInstrumentAR.format_exchange(
            unformatted_fi_test_data.test_exchange_data
        )
        assert result.code == "NYSE"
        assert type(result).__name__ == "Exchange"

    def test_format_historical_data_valid_list(self, unformatted_fi_test_data):
        """
        Test that the `format_historical_data` method correctly formats historical data.

        Args:
            - unformatted_fi_test_data: Fixture providing unformatted test data.

        Assertions:
            - The formatted historical data has the correct code
            - The type of the formatted data is "HistoricalData".

        Raises:
            - AssertionError: If the historical data is not formatted correctly.
        """
        result = FinancialInstrumentAR.format_historical_data(
            unformatted_fi_test_data.test_historical_data_1
        )
        assert result.code == "ABC"
        assert type(result).__name__ == "HistoricalData"

    def test_format_technical_data_valid_data(self, unformatted_fi_test_data):
        """
        Test that the `format_technical_data` method correctly formats technical data.

        Args:
            - unformatted_fi_test_data: Fixture providing unformatted test data.

        Assertions:
            - The formatted technical data has the correct Beta value.
            - The type of the formatted data is "TechnicalData".

        Raises:
            - AssertionError: If the technical data is not formatted correctly.
        """
        result = FinancialInstrumentAR.format_technical_data(
            unformatted_fi_test_data.test_technical_data_1
        )
        assert str(result.Beta) == "1.2"
        assert type(result).__name__ == "TechnicalData"
