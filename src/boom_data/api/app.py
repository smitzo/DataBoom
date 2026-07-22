"""FastAPI application factory for Boom Data."""

from __future__ import annotations

from fastapi import FastAPI

from boom_data import __version__
from boom_data.api.routes import router
from boom_data.core.config import Settings, get_settings
from boom_data.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured FastAPI application instance."""

    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    app = FastAPI(
        title="Boom Data API",
        description="Synthetic data generation API for relational, document, and graph workflows.",
        version=__version__,
    )
    app.state.settings = active_settings
    app.include_router(router)
    return app
