"""Planner interface and always-available deterministic implementation.

Purpose:
    Convert a provider-neutral request into a validated proposal without coupling
    generation to any external model vendor.

Data flow:
    `PlannerRequest` -> planner decision -> proposal ID and telemetry ->
    `PlanProposal`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Protocol

from databoom.planning.models import (
    PlanDecision,
    PlannerMode,
    PlannerRequest,
    PlannerTelemetry,
    PlanProposal,
    PlanResource,
    PlanResourceKind,
)
from databoom.planning.prompts import (
    build_prompt_cache_key,
    load_prompt_pack,
    schema_fingerprint,
)

PLANNER_VERSION = "1"


class Planner(Protocol):
    """Replaceable generation-planning boundary."""

    def propose(self, request: PlannerRequest) -> PlanProposal:
        """Return a validated, unapproved plan proposal."""


class DeterministicPlanner:
    """Build useful plans without network access or model credits."""

    def propose(self, request: PlannerRequest) -> PlanProposal:
        pack = load_prompt_pack()
        fingerprint = schema_fingerprint(request.resources)
        decision = PlanDecision(
            summary=(
                f"Generate {sum(resource.default_count for resource in request.resources):,} "
                f"{request.product_kind.value} records across {len(request.resources)} resources."
            ),
            resources=tuple(
                PlanResource(
                    name=resource.name,
                    kind=resource.kind,
                    target_count=resource.default_count,
                    strategy=_default_strategy(resource.kind),
                    notes=_default_notes(resource.kind),
                )
                for resource in request.resources
            ),
            constraints=_constraints_for(request),
            warnings=(),
        )
        telemetry = PlannerTelemetry(
            mode=PlannerMode.DETERMINISTIC,
            prompt_pack_version=pack.version,
            schema_fingerprint=fingerprint,
            prompt_cache_key=build_prompt_cache_key(
                product_kind=request.product_kind,
                planner_version=PLANNER_VERSION,
                schema_hash=fingerprint,
                prompt_pack_version=pack.version,
            ),
        )
        return proposal_from_decision(request, decision, telemetry)


def proposal_from_decision(
    request: PlannerRequest,
    decision: PlanDecision,
    telemetry: PlannerTelemetry,
) -> PlanProposal:
    """Validate provider output against the request and build a stable proposal."""

    expected = {resource.name: resource for resource in request.resources}
    received = {resource.name: resource for resource in decision.resources}
    if received.keys() != expected.keys():
        missing = sorted(expected.keys() - received.keys())
        unknown = sorted(received.keys() - expected.keys())
        raise ValueError(
            f"planner resources do not match request; missing={missing}, unknown={unknown}"
        )
    for name, resource in received.items():
        if resource.kind != expected[name].kind:
            raise ValueError(f"planner changed resource kind for {name}")

    plan_payload = {
        "planner_version": PLANNER_VERSION,
        "product_id": request.product_id,
        "product_kind": request.product_kind,
        "intent": request.intent,
        "seed": request.seed,
        "output_formats": request.output_formats,
        "decision": decision.model_dump(mode="json"),
    }
    digest = hashlib.sha256(
        json.dumps(plan_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return PlanProposal(
        plan_id=f"plan_{digest}",
        planner_version=PLANNER_VERSION,
        product_id=request.product_id,
        product_kind=request.product_kind,
        intent=request.intent,
        seed=request.seed,
        output_formats=request.output_formats,
        decision=decision,
        telemetry=telemetry,
    )


def _default_strategy(kind: PlanResourceKind) -> str:
    return {
        PlanResourceKind.TABLE: "schema-aware deterministic rows",
        PlanResourceKind.COLLECTION: "nested deterministic documents",
        PlanResourceKind.NODE: "stable labeled nodes",
        PlanResourceKind.EDGE: "endpoint-safe deterministic edges",
    }[kind]


def _default_notes(kind: PlanResourceKind) -> str:
    if kind == PlanResourceKind.EDGE:
        return "Resolve source and target IDs from generated node sets."
    if kind == PlanResourceKind.TABLE:
        return "Preserve primary keys, foreign keys, nullability, and type constraints."
    if kind == PlanResourceKind.COLLECTION:
        return "Preserve nested fields, stable object IDs, and declared references."
    return "Generate unique IDs before creating dependent relationships."


def _constraints_for(request: PlannerRequest) -> tuple[str, ...]:
    common = (
        "Use the supplied seed for repeatable output.",
        "Validate every artifact before marking the run complete.",
    )
    if request.product_kind.value == "relational":
        return common + ("Generate parent tables before dependent child tables.",)
    if request.product_kind.value == "document":
        return common + ("Keep document references inside generated collection IDs.",)
    return common + ("Reject dangling edge endpoints and duplicate node IDs.",)
