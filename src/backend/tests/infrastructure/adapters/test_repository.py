# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides tests for the `SQLAlchemyFIARRepositoryAdapter` class.

This module includes:
- `TestSQLAlchemyFIARRepositoryAdapter`: Tests for the `SQLAlchemyFIARRepositoryAdapter` class.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.app.infrastructure.adapters.repository import SQLAlchemyFIARRepositoryAdapter

class TestSQLAlchemyFIARRepositoryAdapter:
    """
    Tests for the `SQLAlchemyFIARRepositoryAdapter`.

    Methods:
        - test_get_ticker: Tests that the `get_ticker` method retrieves a ticker.
        - test_get_exchange: Tests that the `get_exchange` method retrieves an exchange.
        - test_get_historical_data: Tests that the `get_historical_data` method retrieves historical data.
        - test_get_technical_data: Tests that the `get_technical_data` method retrieves technical data.
        - test_get_ticker_with_technical_and_historical_data: Tests that the `get_ticker_with_technical_and_historical_data` method retrieves data.
        - test_add_ticker: Tests that the `add_ticker` method adds a ticker.
        - test_add_exchange: Tests that the `add_exchange` method adds an exchange.
        - test_add_historical_data: Tests that the `add_historical_data` method adds historical data.
        - test_add_historical_data_bulk: Tests that the `add_historical_data_bulk` method adds historical data in bulk.
        - test_add_technical_data: Tests that the `add_technical_data` method adds technical data.
    """
    # ====================================== #
    #               Unit Tests               #
    # ====================================== #

    async def test_get_ticker(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `get_ticker` method retrieves a ticker.

        Assertions:
            - The method returns the correct ticker.
            - The session's `execute` method is called once with the correct arguments.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the ticker is not retrieved correctly or the error is not raised.
        """
        mock_session = mock_dependencies.session
        mock_ticker = formatted_fi_test_data.test_ticker_data
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_ticker
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)

        ticker = await repo.get_ticker(code="ABC")
        assert ticker == mock_ticker
        mock_result.scalar_one_or_none.assert_called_once()
        mock_session.execute.assert_awaited_once()

        mock_session.execute.side_effect = SQLAlchemyError("Error retrieving ticker.")
        with pytest.raises(SQLAlchemyError, match="Error retrieving ticker."):
            await repo.get_ticker(code="ABC")

    async def test_get_exchange(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `get_exchange` method retrieves an exchange.

        Assertions:
            - The method returns the correct exchange.
            - The session's `execute` method is called once with the correct arguments.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the exchange is not retrieved correctly or the error is not raised.
        """
        mock_session = mock_dependencies.session
        mock_exchange = formatted_fi_test_data.test_exchange_data
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_exchange
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)

        exchange = await repo.get_exchange(code="NYSE")
        assert exchange == mock_exchange
        mock_result.scalar_one_or_none.assert_called_once()
        mock_session.execute.assert_awaited_once()

        mock_session.execute.side_effect = SQLAlchemyError("Error retrieving exchange.")
        with pytest.raises(SQLAlchemyError, match="Error retrieving exchange."):
            await repo.get_exchange(code="NYSE")
    
    async def test_get_historical_data(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `get_historical_data` method retrieves historical data.

        Assertions:
            - The method returns the correct historical data.
            - The session's `execute` method is called once with the correct arguments.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the historical data is not retrieved correctly or the error is not raised.
        """
        mock_session = mock_dependencies.session
        mock_historical_data = formatted_fi_test_data.test_historical_data
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_historical_data
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)
        
        historical_data = await repo.get_historical_data(code="ABC")
        assert historical_data == mock_historical_data
        mock_result.scalars.return_value.all.assert_called_once()
        mock_session.execute.assert_awaited_once()

        mock_session.execute.side_effect = SQLAlchemyError("Error retrieving historical data.")
        with pytest.raises(SQLAlchemyError, match="Error retrieving historical data."):
            await repo.get_historical_data(code="ABC")
    
    async def test_get_technical_data(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `get_technical_data` method retrieves technical data.

        Assertions:
            - The method returns the correct technical data.
            - The session's `execute` method is called once with the correct arguments.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the technical data is not retrieved correctly or the error is not raised.
        """
        mock_session = mock_dependencies.session
        mock_technical_data = formatted_fi_test_data.test_technical_data_1
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_technical_data
        mock_session.execute = AsyncMock(return_value=mock_result)
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)

        technical_data = await repo.get_technical_data(code="ABC")
        assert technical_data == mock_technical_data
        mock_result.scalar_one_or_none.assert_called_once()
        mock_session.execute.assert_awaited_once()

        mock_session.execute.side_effect = SQLAlchemyError("Error retrieving technical data.")
        with pytest.raises(SQLAlchemyError, match="Error retrieving technical data."):
            await repo.get_technical_data(code="ABC")

    async def test_get_ticker_with_technical_and_historical_data(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `get_ticker_with_technical_and_historical_data` method retrieves data.

        Assertions:
            - The method returns the correct ticker, technical data, and historical data.
            - The session's `execute` method is called three times.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the data is not retrieved correctly or the error is not raised.
        """
        mock_ticker = formatted_fi_test_data.test_ticker_data
        mock_technical_data = formatted_fi_test_data.test_technical_data_1
        mock_historical_data = formatted_fi_test_data.test_historical_data_list
        ticker_result = MagicMock()
        ticker_result.scalar_one_or_none.return_value = mock_ticker
        technical_result = MagicMock()
        technical_result.scalar_one_or_none.return_value = mock_technical_data
        historical_result = MagicMock()
        historical_result.scalars.return_value.all.return_value = mock_historical_data
        mock_session = mock_dependencies.session
        mock_session.execute = AsyncMock(side_effect=[ticker_result, technical_result, historical_result])
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)

        ticker, technical_data, historical_data = await repo.get_ticker_with_technical_and_historical_data(code="ABC")
        assert ticker == mock_ticker
        assert technical_data == mock_technical_data
        assert historical_data == mock_historical_data
        assert mock_session.execute.call_count == 3

        mock_session.execute.side_effect = SQLAlchemyError("Error retrieving ticker with technical and historical data.")
        with pytest.raises(SQLAlchemyError, match="Error retrieving ticker with technical and historical data."):
            await repo.get_ticker_with_technical_and_historical_data(code="ABC")

    async def test_add_ticker(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `add_ticker` method adds a ticker.

        Assertions:
            - The session's `add` method is called once with the correct ticker.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the ticker is not added correctly or the error is not raised.
        """
        mock_session = mock_dependencies.session
        mock_ticker = formatted_fi_test_data.test_ticker_data
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)

        await repo.add_ticker(mock_ticker)
        mock_session.add.assert_called_once_with(mock_ticker)

        mock_session.add.side_effect = SQLAlchemyError("Error adding ticker.")
        with pytest.raises(SQLAlchemyError, match="Error adding ticker."):
            await repo.add_ticker(mock_ticker)

    async def test_add_exchange(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `add_exchange` method adds an exchange.

        Assertions:
            - The session's `add` method is called once with the correct exchange.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the exchange is not added correctly or the error is not raised.
        """
        mock_session = mock_dependencies.session
        mock_exchange = formatted_fi_test_data.test_exchange_data
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)

        await repo.add_exchange(mock_exchange)
        mock_session.add.assert_called_once_with(mock_exchange)

        mock_session.add.side_effect = SQLAlchemyError("Error adding exchange.")
        with pytest.raises(SQLAlchemyError, match="Error adding exchange."):
            await repo.add_exchange(mock_exchange)

    async def test_add_historical_data(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `add_historical_data` method adds historical data.

        Assertions:
            - The session's `add` method is called once with the correct historical data.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the historical data is not added correctly or the error is not raised.
        """
        mock_session = mock_dependencies.session
        mock_historical_data = formatted_fi_test_data.test_historical_data
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)

        await repo.add_historical_data(mock_historical_data)
        mock_session.add.assert_called_once_with(mock_historical_data)

        mock_session.add.side_effect = SQLAlchemyError("Error adding historical data.")
        with pytest.raises(SQLAlchemyError, match="Error adding historical data."):
            await repo.add_historical_data(mock_historical_data)
    
    async def test_add_historical_data_bulk(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `add_historical_data_bulk` method adds historical data in bulk.

        Assertions:
            - The session's `add_all` method is called once with the correct historical data list.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the historical data is not added correctly or the error is not raised.
        """
        mock_session = mock_dependencies.session
        mock_historical_data = formatted_fi_test_data.test_historical_data_list
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)

        await repo.add_historical_data_bulk(historical_data_list=mock_historical_data)
        mock_session.add_all.assert_called_once_with(mock_historical_data)

        mock_session.add_all.side_effect = SQLAlchemyError("Error adding historical data in bulk.")
        with pytest.raises(SQLAlchemyError, match="Error adding historical data in bulk."):
            await repo.add_historical_data_bulk(historical_data_list=mock_historical_data)

    async def test_add_technical_data(self, formatted_fi_test_data, mock_dependencies):
        """
        Test that the `add_technical_data` method adds technical data.

        Assertions:
            - The session's `add` method is called once with the correct technical data.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the technical data is not added correctly or the error is not raised.
        """
        mock_session = mock_dependencies.session
        mock_technical_data = formatted_fi_test_data.test_technical_data_1
        repo = SQLAlchemyFIARRepositoryAdapter(mock_session)

        await repo.add_technical_data(mock_technical_data)
        mock_session.add.assert_called_once_with(mock_technical_data)

        mock_session.add.side_effect = SQLAlchemyError("Error adding technical data.")
        with pytest.raises(SQLAlchemyError, match="Error adding technical data."):
            await repo.add_technical_data(mock_technical_data)
