# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

from dependency_injector.wiring import inject
from fastapi import APIRouter

from backend.app.application import events
from backend.app.infrastructure import bootstrap

router = APIRouter()

bootstrap = bootstrap.Bootstrap()


@router.get("/update_financial_instruments")
@inject
async def update_financial_instruments_via_eodhd_api() -> None:
    event_bus = bootstrap.event_bus
    event = events.UpdateFinancialInstruments()
    await event_bus.publish(event)
