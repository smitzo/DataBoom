"""FastAPI application factory for DataBoom.

Purpose:
    Assemble settings, persistence, async run management, middleware, and routes
    into one FastAPI application.

Data flow:
    process startup -> `create_app` -> app state objects -> route handlers use
    those objects through the request context.

Why this layer exists:
    The API can be created with test stores or production settings without global
    singletons. That keeps tests deterministic and makes Docker/local deployments
    use the same route code.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from databoom import __version__
from databoom.api.async_jobs import AsyncRunManager
from databoom.api.auth import ensure_seed_user
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
    # Store runtime services on `app.state` so route handlers stay lightweight and
    # dependency injection can replace them in tests.
    app.state.settings = active_settings
    app.state.state_store = state_store or create_state_store(active_settings)
    ensure_seed_user(app.state.state_store, active_settings)
    app.state.async_run_manager = AsyncRunManager()
    app.router.on_shutdown.append(app.state.async_run_manager.shutdown)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app
