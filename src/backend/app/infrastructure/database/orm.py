# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Provides database table definitions and mappings for financial instrument data.

This module includes:
- Table definitions for `Exchange`, `Ticker`, `HistoricalData`, and `TechnicalData`.
- Function for mapping domain models to database tables using SQLAlchemy's imperative mapping.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    func,
)
from sqlalchemy.orm import registry, relationship
from structlog import stdlib

from backend.app.domain.models import Exchange, HistoricalData, TechnicalData, Ticker

log = stdlib.get_logger(__name__)

mapper_registry = registry()

# ================================== #
#               Tables               #
# ================================== #


exchange = Table(
    "exchange",
    mapper_registry.metadata,
    Column("name", String, nullable=False),
    Column("code", String, primary_key=True),
    Column("operatingmic", String, nullable=False),
    Column("country", String, nullable=False),
    Column("currency", String, nullable=False),
    Column("countryiso2", String, nullable=False),
    Column("countryiso3", String, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "modified_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
)

tickers = Table(
    "tickers",
    mapper_registry.metadata,
    Column("code", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("country", String, nullable=False),
    Column("exchange", String, ForeignKey("exchange.code"), nullable=False),
    Column("currency", String, nullable=False),
    Column("type", String, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "modified_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
)

historical_data = Table(
    "historical_data",
    mapper_registry.metadata,
    Column("code", String, ForeignKey("tickers.code"), primary_key=True),
    Column("datetime", DateTime(timezone=True), primary_key=True),
    Column("open", Float, nullable=False),
    Column("high", Float, nullable=False),
    Column("low", Float, nullable=False),
    Column("close", Float, nullable=False),
    Column("adjusted_close", Float, nullable=False),
    Column("volume", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "modified_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
)

technical_data = Table(
    "technical_data",
    mapper_registry.metadata,
    Column("code", String, ForeignKey("tickers.code"), primary_key=True),
    Column("MarketCapitalization", Integer, nullable=False),
    Column("Beta", Float, nullable=False),
    Column("ema_50d", Float, nullable=False),
    Column("ema_200d", Float, nullable=False),
    Column("hi_250d", Float, nullable=False),
    Column("low_250d", Float, nullable=False),
    Column("prev_close", Float, nullable=False),
    Column("change", Float, nullable=False),
    Column("change_p", Float, nullable=False),
    Column("avgvol_14d", Float, nullable=False),
    Column("avgvol_50d", Float, nullable=False),
    Column("avgvol_200d", Float, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "modified_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
)


# =================================== #
#               Indexes               #
# =================================== #


Index("ix_historical_data_date", historical_data.c.date.desc())


# ===================================== #
#               Functions               #
# ===================================== #


async def start_database_mappers() -> None:
    """
    Map domain models to database tables using SQLAlchemy's imperative mapping.

    This function sets up the relationships between the domain models and the database tables,
    including cascading behavior and lazy loading strategies.

    Raises:
        - Exception: If an error occurs during the mapping process.
    """
    await log.adebug("Starting SQLAlchemy database mappers.")
    try:
        mapper_registry.map_imperatively(
            Exchange,
            exchange,
            properties={
                "ticker": relationship(
                    Ticker, uselist=False, cascade="all, delete-orphan", lazy="selectin"
                )
            },
        )
        mapper_registry.map_imperatively(
            Ticker,
            tickers,
            properties={
                "historical_data": relationship(
                    HistoricalData,
                    cascade="all, delete-orphan",
                    collection_class=list,
                    lazy="selectin",
                ),
                "technical_data": relationship(
                    TechnicalData,
                    uselist=False,
                    cascade="all, delete-orphan",
                    lazy="selectin",
                ),
            },
        )
        mapper_registry.map_imperatively(HistoricalData, historical_data)
        mapper_registry.map_imperatively(TechnicalData, technical_data)
        await log.adebug("Domain models mapped to database.")
    except Exception:
        await log.aexception("Error starting mappers.")
        raise
