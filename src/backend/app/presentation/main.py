# Copyright 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Main application script for running the FastAPI server.

This module includes:
- `create_app`: Creates the FastAPI application instance, including API routes and
  system bootstrapping.
"""

import asyncio

import uvicorn
from fastapi import FastAPI
from structlog import stdlib

from backend.app.infrastructure import bootstrap
from backend.app.presentation import endpoints

log = stdlib.get_logger(__name__)


async def create_app() -> FastAPI:
    """
    Create the FastAPI application instance.

    This function initializes the FastAPI application, includes API routes,
    and bootstraps the application's infrastructure and essential services.

    Returns:
        - FastAPI: The initialized FastAPI application instance.

    Raises:
        - Exception: If an error occurs during application bootstrapping.
    """
    app = FastAPI()
    app.include_router(endpoints.router)
    try:
        await bootstrap.Bootstrap().initialize_application()
    except Exception as error:
        await log.aexception("Error bootstrapping application.", exc_info=error)
        raise
    else:
        return app


async def main():
    "Main entrypoint for the application, handles asyncio setup."
    app = await create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, reload=True)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
