"""Golden contracts for provider-independent generation planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from databoom.planning import DeterministicPlanner, PlannerRequest

CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "planner_golden_cases.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_deterministic_planner_matches_golden_contract(case: dict[str, Any]) -> None:
    """Keep planner output stable across every active generation surface."""

    request = PlannerRequest.model_validate(case["request"])
    proposal = DeterministicPlanner().propose(request)
    expected = case["expected"]

    assert proposal.decision.summary == expected["summary"]
    assert {
        resource.name: resource.strategy for resource in proposal.decision.resources
    } == expected["strategies"]
    assert list(proposal.decision.constraints) == expected["constraints"]
    assert {
        resource.name: resource.target_count for resource in proposal.decision.resources
    } == {
        resource["name"]: resource["default_count"] for resource in case["request"]["resources"]
    }


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_plan_identity_is_stable_for_golden_contract(case: dict[str, Any]) -> None:
    """Make retries idempotent when the reviewed plan content is unchanged."""

    request = PlannerRequest.model_validate(case["request"])

    assert DeterministicPlanner().propose(request).plan_id == DeterministicPlanner().propose(
        request
    ).plan_id
