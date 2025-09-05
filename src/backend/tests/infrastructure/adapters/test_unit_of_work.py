# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides tests for the `SQLAlchemyUnitOfWorkAdapter` class.

This module includes:
- `TestSQLAlchemyUnitOfWorkAdapter`: Tests for the `SQLAlchemyUnitOfWorkAdapter` class.
"""

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.app.infrastructure.adapters.unit_of_work import SQLAlchemyUnitOfWorkAdapter


class TestSQLAlchemyUnitOfWorkAdapter:
    """
    Tests for the `SQLAlchemyUnitOfWorkAdapter` class.

    Methods:
        - test_uow_commit: Tests that the `commit` method commits the database session.
        - test_uow_rollback: Tests that the `rollback` method rolls back the database session.
        - test_uow_aenter: Tests that the `__aenter__` method initializes the database session and begins a transaction.
        - test_uow_aexit: Tests that the `__aexit__` method closes the database session.
        - test_uow_rolls_back_on_error: Tests that the UnitOfWork rolls back on error.
        - test_uow_session_isolation: Tests that the UnitOfWork maintains session isolation.
        - test_uow_fi_repository_integration: Tests that the UnitOfWork properly handles data related to the `SQLAlchemyFIARRepositoryAdapter`.
    """

    # ====================================== #
    #               Unit Tests               #
    # ====================================== #

    async def test_uow_commit(self, mock_dependencies):
        """
        Test that the `commit` method commits the database session.

        Assertions:
            - The `commit` method is called once.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the session is not committed or the error is not raised.
        """
        async with SQLAlchemyUnitOfWorkAdapter(
            mock_dependencies.session_factory
        ) as uow_1:
            await uow_1.commit()
        mock_dependencies.session.commit.assert_awaited_once()

        mock_dependencies.session.commit.side_effect = SQLAlchemyError(
            "Error committing database session."
        )
        with pytest.raises(SQLAlchemyError, match="Error committing database session."):
            async with SQLAlchemyUnitOfWorkAdapter(
                mock_dependencies.session_factory
            ) as uow_2:
                await uow_2.commit()

    async def test_uow_rollback(self, mock_dependencies):
        """
        Test that the `rollback` method rolls back the database session.

        Args:
            - mock_dependencies: Fixture providing mocked dependencies.

        Assertions:
            - The `rollback` method is called once.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the session is not rolled back or the error is not raised.
        """
        async with SQLAlchemyUnitOfWorkAdapter(
            mock_dependencies.session_factory
        ) as uow_1:
            await uow_1.rollback()
        mock_dependencies.session.rollback.assert_awaited_once()

        mock_dependencies.session.rollback.side_effect = SQLAlchemyError(
            "Error rolling back database session."
        )
        with pytest.raises(
            SQLAlchemyError, match="Error rolling back database session."
        ):
            async with SQLAlchemyUnitOfWorkAdapter(
                mock_dependencies.session_factory
            ) as uow_2:
                await uow_2.rollback()

    async def test_uow_aenter(self, mock_dependencies):
        """
        Test that the `__aenter__` method initializes the database session.

        Assertions:
            - The session factory is called once.
            - The session's `__aenter__` method is awaited once.
            - The `financial_instrument` attribute is not None.

        Raises:
            - AssertionError: If the session is not initialized or the error is not raised.
        """
        async with SQLAlchemyUnitOfWorkAdapter(
            mock_dependencies.session_factory
        ) as unit_of_work:
            pass
        mock_dependencies.session_factory.assert_called_once()
        mock_dependencies.session.__aenter__.assert_awaited_once()
        assert unit_of_work.financial_instrument is not None

        mock_dependencies.session_factory.side_effect = SQLAlchemyError(
            "Error initializing database session."
        )
        with pytest.raises(
            SQLAlchemyError, match="Error initializing database session."
        ):
            async with SQLAlchemyUnitOfWorkAdapter(mock_dependencies.session_factory):
                pass

    async def test_uow_aexit(self, mock_dependencies):
        """
        Test that the `__aexit__` method closes the database session.

        Assertions:
            - The session's `__aexit__` method is awaited once.
            - If a `SQLAlchemyError` occurs, it is raised with the correct message.

        Raises:
            - AssertionError: If the session is not closed or the error is not raised.
        """
        async with SQLAlchemyUnitOfWorkAdapter(mock_dependencies.session_factory):
            pass
        mock_dependencies.session.__aexit__.assert_awaited_once()

        mock_dependencies.session.__aexit__.side_effect = SQLAlchemyError(
            "Error closing database session."
        )
        with pytest.raises(SQLAlchemyError, match="Error closing database session."):
            async with SQLAlchemyUnitOfWorkAdapter(mock_dependencies.session_factory):
                pass

    # ============================================= #
    #               Integration Tests               #
    # ============================================= #

    @pytest.mark.integration
    async def test_uow_rolls_back_on_error(
        self, formatted_fi_test_data, real_dependencies
    ):
        """
        Test that the unit of work rolls back on error.

        Args:
            - formatted_fi_test_data: Fixture providing formatted test data.
            - real_dependencies: Fixture providing real dependencies.

        Assertions:
            - If an exception is raised within the unit of work, the changes are rolled back.
            - The fetched data is None after the rollback.

        Raises:
            - AssertionError: If the rollback does not occur or the data is not None.
        """
        unit_of_work = real_dependencies.unit_of_work
        ticker_data = formatted_fi_test_data.test_ticker_data

        try:
            async with unit_of_work() as uow_1:
                await uow_1.financial_instrument.add_ticker(ticker_data)
                raise Exception
        except Exception:
            pass

        async with unit_of_work() as uow_2:
            fetched_data = await uow_2.financial_instrument.get_ticker("ABC")
            assert fetched_data is None

    @pytest.mark.integration
    async def test_uow_session_isolation(
        self, formatted_fi_test_data, real_dependencies
    ):
        """
        Test that the unit of work maintains session isolation.

        Args:
            - formatted_fi_test_data: Fixture providing formatted test data.
            - real_dependencies: Fixture providing real dependencies.

        Assertions:
            - Data added in one unit of work is not visible in another unit of work until committed.

        Raises:
            - AssertionError: If the session isolation is not maintained.
        """
        unit_of_work = real_dependencies.unit_of_work
        exchange_data = formatted_fi_test_data.test_exchange_data

        async with unit_of_work() as uow_1:
            await uow_1.financial_instrument.add_exchange(exchange_data)

        async with unit_of_work() as uow_2:
            fetched_data = await uow_2.financial_instrument.get_exchange("ABC")
            assert fetched_data is None

    @pytest.mark.integration
    async def test_uow_fi_repository_integration(
        self, formatted_fi_test_data, real_dependencies
    ):
        """
        Test that the UnitOfWork properly handles data related to the `SQLAlchemyFIARRepositoryAdapter`.

        Args:
            - formatted_fi_test_data: Fixture providing formatted test data.
            - real_dependencies: Fixture providing real dependencies.

        Assertions:
            - The data is correctly added and committed to the database.
            - The fetched data matches the expected values.
            - The technical data is correctly updated.
            - Non-existing data returns None.

        Raises:
            - AssertionError: If the data is not persisted correctly.
        """
        unit_of_work = real_dependencies.unit_of_work
        exchange_data = formatted_fi_test_data.test_exchange_data
        ticker_data = formatted_fi_test_data.test_ticker_data
        historical_data = formatted_fi_test_data.test_historical_data_list
        technical_data_1 = formatted_fi_test_data.test_technical_data_1
        technical_data_2 = formatted_fi_test_data.test_technical_data_2
        start_date = "2025-01-01"
        end_date = "2025-01-02"

        async with unit_of_work() as uow_1:
            await uow_1.financial_instrument.add_exchange(exchange_data)
            await uow_1.financial_instrument.add_ticker(ticker_data)
            await uow_1.financial_instrument.add_historical_data_bulk(historical_data)
            await uow_1.financial_instrument.add_technical_data(technical_data_1)
            await uow_1.commit()

        async with unit_of_work() as uow_2:
            fetched_exchange = await uow_2.financial_instrument.get_exchange("NYSE")
            fetched_ticker = await uow_2.financial_instrument.get_ticker("ABC")
            fetched_historical_data = (
                await uow_2.financial_instrument.get_historical_data(
                    "ABC", start_date, end_date
                )
            )
            fetched_technical_data = (
                await uow_2.financial_instrument.get_technical_data("ABC")
            )
            (
                bundled_ticker_data,
                bundled_technical_data,
                bundled_historical_data,
            ) = await uow_2.financial_instrument.get_ticker_with_technical_and_historical_data(
                "ABC", start_date, end_date
            )
            assert fetched_exchange.code == "NYSE"
            assert fetched_ticker.code == "ABC"
            assert len(fetched_historical_data) == 2
            assert fetched_technical_data.code == "ABC"
            assert bundled_ticker_data.code == "ABC"
            assert bundled_technical_data.code == "ABC"
            assert len(bundled_historical_data) == 2

        async with unit_of_work() as uow_3:
            await uow_3.financial_instrument.update_technical_data(technical_data_2)
            await uow_3.commit()

        async with unit_of_work() as uow_4:
            updated_data = await uow_4.financial_instrument.get_technical_data("ABC")
            assert updated_data.code == "ABC"
            assert updated_data.Beta == 2.4

            non_existing_data = await uow_4.financial_instrument.get_ticker_with_technical_and_historical_data(
                "NOTEXIST"
            )
            (
                non_existing_ticker_data,
                non_existing_technical_data,
                non_existing_historical_data,
            ) = non_existing_data
            assert non_existing_ticker_data is None
            assert non_existing_technical_data is None
            assert len(non_existing_historical_data) == 0
