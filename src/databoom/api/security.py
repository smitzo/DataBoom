"""API security dependencies."""

from __future__ import annotations

from secrets import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from databoom.core.config import Settings


def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Require an API key when one is configured for the service."""

    settings: Settings = request.app.state.settings
    if settings.api_key is None:
        return

    expected_api_key = settings.api_key.get_secret_value()
    if x_api_key is None or not compare_digest(x_api_key, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="valid api key required",
            headers={"WWW-Authenticate": "APIKey"},
        )
