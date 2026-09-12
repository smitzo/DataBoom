from databoom.planning import (
    DeterministicPlanner,
    PlannerMode,
    PlannerRequest,
    PlanResourceInput,
    PlanResourceKind,
    PlanReviewStatus,
    ProductKind,
    build_prompt_cache_key,
    load_prompt_pack,
    schema_fingerprint,
)


def test_deterministic_planner_builds_repeatable_reviewable_plan() -> None:
    request = _graph_request()

    first = DeterministicPlanner().propose(request)
    second = DeterministicPlanner().propose(request)

    assert first.plan_id == second.plan_id
    assert first.review_status == PlanReviewStatus.DRAFT
    assert first.telemetry.mode == PlannerMode.DETERMINISTIC
    assert first.telemetry.cached_input_tokens == 0
    assert {resource.name: resource.target_count for resource in first.decision.resources} == {
        "Customer": 25,
        "OWNS": 40,
    }
    assert "dangling edge endpoints" in first.decision.constraints[-1]


def test_schema_fingerprint_ignores_resource_order_but_tracks_contract_changes() -> None:
    request = _graph_request()
    reversed_resources = tuple(reversed(request.resources))

    assert schema_fingerprint(request.resources) == schema_fingerprint(reversed_resources)

    changed = request.resources[0].model_copy(update={"default_count": 26})
    assert schema_fingerprint(request.resources) != schema_fingerprint(
        (changed, request.resources[1])
    )


def test_prompt_pack_contains_strict_output_schema_and_stable_cache_key() -> None:
    request = _graph_request()
    pack = load_prompt_pack()
    fingerprint = schema_fingerprint(request.resources)
    cache_key = build_prompt_cache_key(
        product_kind=request.product_kind,
        planner_version="1",
        schema_hash=fingerprint,
        prompt_pack_version=pack.version,
    )

    assert pack.output_schema["additionalProperties"] is False
    assert "bulk records" in pack.system
    assert cache_key.startswith("databoom:graph:1:")
    assert len(cache_key) <= 64
    assert request.intent not in cache_key


def _graph_request() -> PlannerRequest:
    return PlannerRequest(
        product_id="graph-boom",
        product_kind=ProductKind.GRAPH,
        intent="Generate an account ownership graph for integration tests.",
        seed="planner-test",
        output_formats=("json", "csv"),
        resources=(
            PlanResourceInput(
                name="Customer",
                kind=PlanResourceKind.NODE,
                default_count=25,
                attributes=("segment", "status"),
            ),
            PlanResourceInput(
                name="OWNS",
                kind=PlanResourceKind.EDGE,
                default_count=40,
                source_resource="Customer",
                target_resource="Customer",
            ),
        ),
    )
