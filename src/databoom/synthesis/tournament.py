"""Local single-table candidate orchestration and experimental decisions."""

from __future__ import annotations

from databoom.synthesis.adapters import (
    AdapterRegistry,
    SynthesizerUnavailableError,
    build_default_registry,
)
from databoom.synthesis.contracts import (
    AdapterAvailability,
    CandidateDecision,
    CandidateResult,
    CandidateStatus,
    FitConfig,
    TournamentReport,
    TournamentRequest,
)
from databoom.synthesis.evaluation import evaluate_candidate
from databoom.synthesis.io import (
    relative_to_root,
    resolve_within,
    sha256_file,
    stable_digest,
    write_model_json,
)
from databoom.synthesis.splitting import load_split_manifest, verify_split_artifacts


def run_tournament(
    request: TournamentRequest,
    *,
    registry: AdapterRegistry | None = None,
) -> TournamentReport:
    """Fit, sample, and evaluate candidates while preserving independent failures."""

    request.dataset_contract.require_training_eligible()
    split_manifest_path = request.split_manifest_path.resolve()
    split_manifest = load_split_manifest(split_manifest_path)
    verify_split_artifacts(split_manifest, split_manifest_path)
    if split_manifest.columns != request.dataset_contract.column_names:
        raise ValueError("split columns do not match the reviewed dataset contract")

    active_registry = registry or build_default_registry()
    resolved_adapters = {}
    unknown_candidates: list[str] = []
    for candidate in request.candidates:
        try:
            resolved_adapters[candidate.adapter_name] = active_registry.get(
                candidate.adapter_name
            )
        except KeyError:
            unknown_candidates.append(candidate.adapter_name)
    if unknown_candidates:
        available = ", ".join(
            capability.name for capability in active_registry.capabilities()
        )
        raise ValueError(
            "unknown synthesizer adapters: "
            f"{', '.join(unknown_candidates)}; available adapters: {available}"
        )

    experiment_root = request.experiment_root.resolve()
    report_path = experiment_root / "tournament-report.json"
    if report_path.exists() and not request.overwrite:
        raise FileExistsError(f"tournament report already exists: {report_path}")
    experiment_root.mkdir(parents=True, exist_ok=True)

    split_root = split_manifest_path.parent
    training_csv = resolve_within(split_root, split_manifest.training.path)
    holdout_csv = resolve_within(split_root, split_manifest.holdout.path)
    experiment_id = (
        "experiment_"
        + stable_digest(
            split_manifest.split_id,
            request.dataset_contract.model_dump_json(),
            request.fit_seed,
            request.evaluation_seed,
            str(request.sample_row_count),
            "|".join(candidate.model_dump_json() for candidate in request.candidates),
        )[:24]
    )

    results: list[CandidateResult] = []
    for candidate in request.candidates:
        adapter = resolved_adapters[candidate.adapter_name]
        capabilities = adapter.capabilities
        if capabilities.availability != AdapterAvailability.AVAILABLE:
            results.append(
                CandidateResult(
                    adapter_name=candidate.adapter_name,
                    status=CandidateStatus.UNAVAILABLE,
                    capabilities=capabilities,
                    error_type="SynthesizerUnavailableError",
                    error_message=capabilities.unavailable_reason,
                )
            )
            continue

        candidate_dir = experiment_root / _safe_candidate_directory(candidate.adapter_name)
        if candidate_dir.exists() and not request.overwrite:
            raise FileExistsError(f"candidate directory already exists: {candidate_dir}")
        candidate_dir.mkdir(parents=True, exist_ok=True)
        try:
            model_manifest = adapter.fit(
                training_csv,
                request.dataset_contract,
                experiment_root,
                candidate_dir / "model",
                FitConfig(seed=request.fit_seed, hyperparameters=candidate.hyperparameters),
            )
            if model_manifest.training_partition_sha256 != split_manifest.training.sha256:
                raise ValueError("model lineage does not match the training partition")
            sample = adapter.sample(
                model_manifest,
                experiment_root,
                candidate_dir / "sample.csv",
                row_count=request.sample_row_count,
                seed=request.evaluation_seed,
            )
            repeated_sample = adapter.sample(
                model_manifest,
                experiment_root,
                candidate_dir / "sample-repeated.csv",
                row_count=request.sample_row_count,
                seed=request.evaluation_seed,
            )
            reproducible = sample.sha256 == repeated_sample.sha256
            sample_path = resolve_within(experiment_root, sample.path)
            if sha256_file(sample_path) != sample.sha256:
                raise ValueError("sample artifact checksum mismatch")
            quality = evaluate_candidate(
                adapter_name=candidate.adapter_name,
                dataset=request.dataset_contract,
                training_csv=training_csv,
                holdout_csv=holdout_csv,
                synthetic_csv=sample_path,
                expected_sample_rows=request.sample_row_count,
                reproducible_sample=reproducible,
                model_manifest=model_manifest,
                sample_artifact=sample,
                policy=request.policy,
            )
            quality_path = candidate_dir / "quality-report.json"
            write_model_json(quality_path, quality)
            results.append(
                CandidateResult(
                    adapter_name=candidate.adapter_name,
                    status=CandidateStatus.COMPLETED,
                    capabilities=capabilities,
                    model_manifest_path=relative_to_root(
                        experiment_root, candidate_dir / "model" / "model-manifest.json"
                    ),
                    sample_path=sample.path,
                    quality_report_path=relative_to_root(experiment_root, quality_path),
                    quality_report=quality,
                )
            )
        except SynthesizerUnavailableError as exc:
            results.append(
                CandidateResult(
                    adapter_name=candidate.adapter_name,
                    status=CandidateStatus.UNAVAILABLE,
                    capabilities=adapter.capabilities,
                    error_type=type(exc).__name__,
                    error_message="optional provider is unavailable in the active ML worker",
                )
            )
        except Exception as exc:
            results.append(
                CandidateResult(
                    adapter_name=candidate.adapter_name,
                    status=CandidateStatus.FAILED,
                    capabilities=adapter.capabilities,
                    error_type=type(exc).__name__,
                    error_message="candidate execution failed; inspect the isolated worker logs",
                )
            )

    passing = [
        result
        for result in results
        if result.status == CandidateStatus.COMPLETED
        and result.quality_report is not None
        and _implemented_gates_pass(result.quality_report)
    ]
    completed = [result for result in results if result.status == CandidateStatus.COMPLETED]
    if passing:
        recommended = min(
            passing,
            key=lambda result: (result.capabilities.complexity_tier, result.adapter_name),
        )
        decision = CandidateDecision.RECOMMENDED_FOR_CONTROLLED_EVALUATION
        recommended_adapter = recommended.adapter_name
    elif completed:
        decision = CandidateDecision.NOT_RECOMMENDED
        recommended_adapter = None
    else:
        decision = CandidateDecision.NO_ELIGIBLE_CANDIDATE
        recommended_adapter = None

    report = TournamentReport(
        experiment_id=experiment_id,
        split_id=split_manifest.split_id,
        sample_row_count=request.sample_row_count,
        evaluation_seed=request.evaluation_seed,
        candidates=tuple(results),
        decision=decision,
        recommended_adapter=recommended_adapter,
        release_approved=False,
    )
    write_model_json(report_path, report)
    return report


def _implemented_gates_pass(report: object) -> bool:
    from databoom.synthesis.contracts import GateStatus, QualityReport

    if not isinstance(report, QualityReport):
        return False
    implemented = [gate for gate in report.gates if gate.name != "production_evidence"]
    return bool(implemented) and all(gate.status == GateStatus.PASSED for gate in implemented)


def _safe_candidate_directory(name: str) -> str:
    normalized = "".join(
        character if character.isalnum() or character in "-_" else "-" for character in name
    )
    if not normalized:
        raise ValueError("candidate name cannot produce an empty artifact directory")
    return normalized
