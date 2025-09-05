# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides tests for database mapping functionality.

This module includes:
- `TestORM`: Tests for the ORM (Object-Relational Mapping) setup and mapping.
"""

import pytest
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import clear_mappers

from backend.app.infrastructure.database import orm

class TestORM:
    """
    Tests for the ORM (Object-Relational Mapping) setup and mapping.

    Methods:
        - test_remapping_failure: Tests that attempting to remap the database after it has already been mapped raises an ArgumentError.
        - test_successful_database_mapping: Tests that the database mapping is successful and includes the expected tables.
    """
    # ====================================== #
    #               Unit Tests               #
    # ====================================== #

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
    async def test_remapping_failure(self, real_dependencies):
        """
        Test that attempting to remap the database after it has already been mapped raises an ArgumentError.

        Assertions:
            - Calling `start_database_mappers` a second time raises an ArgumentError.

        Raises:
            - AssertionError: If the ArgumentError is not raised.
        """
        with pytest.raises(ArgumentError):
            await orm.start_database_mappers()

    async def test_successful_database_mapping(self, real_dependencies):
        """
        Test that the database mapping is successful and includes the expected tables.

        Assertions:
            - The mapper registry contains the expected tables.

        Raises:
            - AssertionError: If the expected tables are not present in the mapper registry.
        """
        assert 'exchange' in orm.mapper_registry.metadata.tables
        assert 'tickers' in orm.mapper_registry.metadata.tables
        assert 'historical_data' in orm.mapper_registry.metadata.tables
        assert 'technical_data' in orm.mapper_registry.metadata.tables