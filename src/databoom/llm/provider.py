"""LLM provider policy for planning-assisted workflows.

Purpose:
    Decide which LLM credential source, if any, should be used for a planning
    request.

Data flow:
    deployment settings + optional user-supplied key -> provider policy -> future
    planner can either call an LLM or use the deterministic engine fallback.

Why this approach:
    DataBoom must keep running for demos, judges, and production fallbacks even
    when platform credits are exhausted or no key is configured. The policy layer
    makes the LLM optional and keeps secret handling away from generation code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import SecretStr

from databoom.core.config import Settings


class LLMProviderMode(StrEnum):
    """Selected source for an LLM-assisted operation."""

    USER_KEY = "user_key"
    PLATFORM_KEY = "platform_key"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


@dataclass(frozen=True)
class LLMProviderPolicy:
    """Resolved LLM usage policy for one request."""

    active_mode: LLMProviderMode
    default_model: str
    token_limit: int
    platform_key_configured: bool
    user_key_supplied: bool
    deterministic_fallback_available: bool = True

    @property
    def llm_enabled(self) -> bool:
        """Return whether the resolved policy can make an external LLM call."""

        return self.active_mode in {LLMProviderMode.USER_KEY, LLMProviderMode.PLATFORM_KEY}


def resolve_llm_provider_policy(
    settings: Settings,
    *,
    user_api_key: SecretStr | None = None,
) -> LLMProviderPolicy:
    """Resolve request-level LLM policy without exposing secret values."""

    user_key_supplied = _has_secret(user_api_key)
    platform_key_configured = _has_secret(settings.llm_platform_api_key)

    if user_key_supplied:
        active_mode = LLMProviderMode.USER_KEY
    elif platform_key_configured:
        active_mode = LLMProviderMode.PLATFORM_KEY
    else:
        active_mode = LLMProviderMode.DETERMINISTIC_FALLBACK

    return LLMProviderPolicy(
        active_mode=active_mode,
        default_model=settings.llm_default_model,
        token_limit=settings.llm_request_token_limit,
        platform_key_configured=platform_key_configured,
        user_key_supplied=user_key_supplied,
    )


def _has_secret(value: SecretStr | None) -> bool:
    if value is None:
        return False
    return bool(value.get_secret_value().strip())
