"""FastAPI application factory for DataBoom."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from databoom import __version__
from databoom.api.routes import router
from databoom.api.state import StateStore, create_state_store
from databoom.core.config import Settings, get_settings
from databoom.core.logging import configure_logging


def create_app(settings: Settings | None = None, state_store: StateStore | None = None) -> FastAPI:
    """Create a configured FastAPI application instance."""

    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    app = FastAPI(
        title="DataBoom API",
        description="Synthetic data generation API for relational, document, and graph workflows.",
        version=__version__,
    )
    app.state.settings = active_settings
    app.state.state_store = state_store or create_state_store(active_settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app
