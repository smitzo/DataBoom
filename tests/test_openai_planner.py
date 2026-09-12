from types import SimpleNamespace

from pydantic import SecretStr

from databoom.core.config import Settings
from databoom.planning import (
    OpenAIPlanner,
    PlannerMode,
    PlannerRequest,
    PlanningService,
    PlanResourceInput,
    PlanResourceKind,
    ProductKind,
)
from databoom.planning.openai_planner import OpenAIPlannerError


class FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.payload = None

    def create(self, **payload):
        self.payload = payload
        return SimpleNamespace(
            output_text=self.output_text,
            usage=SimpleNamespace(
                input_tokens=1_400,
                output_tokens=180,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=1_024,
                    cache_write_tokens=0,
                ),
            ),
        )


def test_openai_planner_uses_strict_schema_and_captures_cache_metrics() -> None:
    responses = FakeResponses(_decision_json())
    client = SimpleNamespace(responses=responses)
    planner = OpenAIPlanner(
        api_key=SecretStr("test-key"),
        model="planner-test-model",
        max_output_tokens=800,
        timeout_seconds=5,
        max_retries=0,
        client=client,
    )

    proposal = planner.propose(_request())

    assert proposal.telemetry.mode == PlannerMode.OPENAI
    assert proposal.telemetry.cached_input_tokens == 1_024
    assert proposal.telemetry.input_tokens == 1_400
    assert responses.payload["text"]["format"]["strict"] is True
    assert responses.payload["prompt_cache_key"].startswith("databoom:graph:1:")
    assert "PLAN REQUEST" not in responses.payload["instructions"]
    assert "PLAN REQUEST" in responses.payload["input"][0]["content"]


def test_planning_service_uses_deterministic_mode_without_api_key() -> None:
    settings = Settings(ENV="test", DATABOOM_LLM_PLATFORM_API_KEY="")

    proposal = PlanningService(settings).propose(_request())

    assert proposal.telemetry.mode == PlannerMode.DETERMINISTIC
    assert proposal.telemetry.fallback_reason is None


def test_planning_service_falls_back_when_hosted_planner_fails(monkeypatch) -> None:
    class FailingPlanner:
        def __init__(self, **_kwargs) -> None:
            pass

        def propose(self, _request: PlannerRequest):
            raise OpenAIPlannerError("hosted planner request failed")

    monkeypatch.setattr("databoom.planning.openai_planner.OpenAIPlanner", FailingPlanner)
    settings = Settings(ENV="test", DATABOOM_LLM_PLATFORM_API_KEY="platform-test-key")

    proposal = PlanningService(settings).propose(_request())

    assert proposal.telemetry.mode == PlannerMode.DETERMINISTIC
    assert proposal.telemetry.fallback_reason == "hosted planner request failed"


def _request() -> PlannerRequest:
    return PlannerRequest(
        product_id="graph-boom",
        product_kind=ProductKind.GRAPH,
        intent="Generate a compact ownership graph.",
        seed="hosted-planner-test",
        output_formats=("json", "csv"),
        resources=(
            PlanResourceInput(
                name="Customer",
                kind=PlanResourceKind.NODE,
                default_count=10,
                attributes=("status",),
            ),
            PlanResourceInput(
                name="OWNS",
                kind=PlanResourceKind.EDGE,
                default_count=12,
                source_resource="Customer",
                target_resource="Customer",
            ),
        ),
    )


def _decision_json() -> str:
    return """{
      "summary": "Generate a compact ownership graph.",
      "resources": [
        {
          "name": "Customer",
          "kind": "node",
          "target_count": 10,
          "strategy": "stable labeled nodes",
          "notes": "Generate node IDs first."
        },
        {
          "name": "OWNS",
          "kind": "edge",
          "target_count": 12,
          "strategy": "endpoint-safe deterministic edges",
          "notes": "Resolve both endpoints from Customer IDs."
        }
      ],
      "constraints": ["Reject dangling edge endpoints."],
      "warnings": []
    }"""
