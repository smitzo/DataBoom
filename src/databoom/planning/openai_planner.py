"""OpenAI Responses API adapter for structured generation planning.

Purpose:
    Ask a hosted model for a small plan decision while keeping DataBoom's
    deterministic engine, validation, and review workflow authoritative.

Data flow:
    normalized `PlannerRequest` + stable prompt pack -> Responses API strict JSON
    Schema output -> `PlanDecision` validation -> `PlanProposal`.

Security and reliability:
    The request contains metadata, never source rows. API keys stay in memory. A
    bounded timeout and retry policy prevents planning from blocking generation,
    and `PlanningService` falls back to the deterministic planner on every provider
    failure.
"""

from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any

from openai import OpenAI
from pydantic import SecretStr, ValidationError

from databoom.core.config import Settings
from databoom.llm.provider import LLMProviderMode, resolve_llm_provider_policy
from databoom.planning.models import (
    PlanDecision,
    PlannerMode,
    PlannerRequest,
    PlannerTelemetry,
    PlanProposal,
)
from databoom.planning.planner import (
    PLANNER_VERSION,
    DeterministicPlanner,
    proposal_from_decision,
)
from databoom.planning.prompts import (
    build_prompt_cache_key,
    load_prompt_pack,
    schema_fingerprint,
)

LOGGER = logging.getLogger(__name__)


class OpenAIPlannerError(RuntimeError):
    """Raised when hosted planning cannot produce a valid decision."""


class OpenAIPlanner:
    """Strict structured-output planner backed by the Responses API."""

    def __init__(
        self,
        *,
        api_key: SecretStr,
        model: str,
        max_output_tokens: int,
        timeout_seconds: float,
        max_retries: int,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.client = client or OpenAI(
            api_key=api_key.get_secret_value(),
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def propose(self, request: PlannerRequest) -> PlanProposal:
        """Return a validated proposal or raise a provider-neutral planner error."""

        pack = load_prompt_pack()
        fingerprint = schema_fingerprint(request.resources)
        cache_key = build_prompt_cache_key(
            product_kind=request.product_kind,
            planner_version=PLANNER_VERSION,
            schema_hash=fingerprint,
            prompt_pack_version=pack.version,
        )
        started = perf_counter()
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=_stable_instructions(pack),
                input=[{"role": "user", "content": _variable_prompt(request)}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "databoom_generation_plan",
                        "strict": True,
                        "schema": pack.output_schema,
                    }
                },
                prompt_cache_key=cache_key,
                max_output_tokens=self.max_output_tokens,
            )
            decision = PlanDecision.model_validate_json(response.output_text)
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise OpenAIPlannerError("hosted planner returned an invalid plan") from error
        except Exception as error:
            raise OpenAIPlannerError("hosted planner request failed") from error

        usage = getattr(response, "usage", None)
        input_details = getattr(usage, "input_tokens_details", None)
        telemetry = PlannerTelemetry(
            mode=PlannerMode.OPENAI,
            model=self.model,
            prompt_pack_version=pack.version,
            schema_fingerprint=fingerprint,
            prompt_cache_key=cache_key,
            input_tokens=_metric(usage, "input_tokens"),
            cached_input_tokens=_metric(input_details, "cached_tokens"),
            cache_write_tokens=_metric(input_details, "cache_write_tokens"),
            output_tokens=_metric(usage, "output_tokens"),
            latency_ms=round((perf_counter() - started) * 1_000),
        )
        proposal = proposal_from_decision(request, decision, telemetry)
        _log_telemetry(telemetry, success=True)
        return proposal


class PlanningService:
    """Resolve provider policy and guarantee a deterministic proposal."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.deterministic = DeterministicPlanner()

    def propose(
        self,
        request: PlannerRequest,
        *,
        user_api_key: SecretStr | None = None,
    ) -> PlanProposal:
        policy = resolve_llm_provider_policy(self.settings, user_api_key=user_api_key)
        if not policy.llm_enabled:
            return self.deterministic.propose(request)

        api_key = (
            user_api_key
            if policy.active_mode == LLMProviderMode.USER_KEY
            else self.settings.llm_platform_api_key
        )
        if api_key is None:
            return self.deterministic.propose(request)

        try:
            return OpenAIPlanner(
                api_key=api_key,
                model=policy.default_model,
                max_output_tokens=policy.token_limit,
                timeout_seconds=self.settings.llm_timeout_seconds,
                max_retries=self.settings.llm_max_retries,
            ).propose(request)
        except OpenAIPlannerError as error:
            fallback = self.deterministic.propose(request)
            telemetry = fallback.telemetry.model_copy(update={"fallback_reason": str(error)})
            _log_telemetry(telemetry, success=False)
            return fallback.model_copy(update={"telemetry": telemetry})


def _stable_instructions(pack: Any) -> str:
    """Keep reusable instructions and output schema before variable request data."""

    schema = json.dumps(pack.output_schema, sort_keys=True, separators=(",", ":"))
    return f"{pack.stable_prefix}\n\nSTRICT OUTPUT JSON SCHEMA\n{schema}"


def _variable_prompt(request: PlannerRequest) -> str:
    payload = request.model_dump(mode="json")
    return "PLAN REQUEST\n" + json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _metric(container: Any, field: str) -> int:
    value = getattr(container, field, 0) if container is not None else 0
    return value if isinstance(value, int) and value >= 0 else 0


def _log_telemetry(telemetry: PlannerTelemetry, *, success: bool) -> None:
    LOGGER.info(
        "planner completed",
        extra={
            "planner_success": success,
            "planner_mode": telemetry.mode,
            "planner_model": telemetry.model,
            "prompt_pack_version": telemetry.prompt_pack_version,
            "schema_fingerprint": telemetry.schema_fingerprint,
            "prompt_cache_key": telemetry.prompt_cache_key,
            "input_tokens": telemetry.input_tokens,
            "cached_input_tokens": telemetry.cached_input_tokens,
            "cache_write_tokens": telemetry.cache_write_tokens,
            "output_tokens": telemetry.output_tokens,
            "latency_ms": telemetry.latency_ms,
            "fallback_reason": telemetry.fallback_reason,
        },
    )
