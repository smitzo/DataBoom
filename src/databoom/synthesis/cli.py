"""Dedicated local worker CLI for source-trained synthesis experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from databoom.synthesis.adapters import build_default_registry
from databoom.synthesis.contracts import (
    CandidateConfig,
    DatasetContract,
    EvaluationPolicy,
    SplitRatios,
    SplitRequest,
    TournamentRequest,
)
from databoom.synthesis.splitting import split_csv_dataset
from databoom.synthesis.tournament import run_tournament

app = typer.Typer(
    name="databoom-ml",
    help="Isolated statistical and neural synthesis experiment worker.",
    no_args_is_help=True,
)


@app.command("capabilities")
def capabilities_command() -> None:
    """Print adapter capability and optional-dependency availability as JSON."""

    registry = build_default_registry()
    payload = [capability.model_dump(mode="json") for capability in registry.capabilities()]
    import json

    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("split")
def split_command(
    source_path: Annotated[
        Path,
        typer.Argument(exists=True, readable=True, help="Source CSV to partition."),
    ],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for split CSVs and manifest."),
    ],
    seed: Annotated[str, typer.Option("--seed")] = "0",
    training_ratio: Annotated[float, typer.Option("--training-ratio")] = 0.70,
    validation_ratio: Annotated[float, typer.Option("--validation-ratio")] = 0.15,
    holdout_ratio: Annotated[float, typer.Option("--holdout-ratio")] = 0.15,
    group_columns: Annotated[
        list[str] | None,
        typer.Option("--group-column", help="Subject column kept in one partition. Repeatable."),
    ] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Create deterministic train, validation, and holdout CSV artifacts."""

    manifest = split_csv_dataset(
        SplitRequest(
            source_path=source_path,
            output_dir=output_dir,
            seed=seed,
            ratios=SplitRatios(
                training=training_ratio,
                validation=validation_ratio,
                holdout=holdout_ratio,
            ),
            group_columns=tuple(group_columns or ()),
            overwrite=overwrite,
        )
    )
    typer.echo(f"split_id: {manifest.split_id}")
    typer.echo(f"training_rows: {manifest.training.row_count}")
    typer.echo(f"validation_rows: {manifest.validation.row_count}")
    typer.echo(f"holdout_rows: {manifest.holdout.row_count}")
    typer.echo(f"manifest: {output_dir / 'split-manifest.json'}")


@app.command("tournament")
def tournament_command(
    split_manifest_path: Annotated[
        Path,
        typer.Argument(exists=True, readable=True, help="Validated split-manifest.json."),
    ],
    contract_path: Annotated[
        Path,
        typer.Argument(exists=True, readable=True, help="Reviewed DatasetContract JSON."),
    ],
    experiment_root: Annotated[
        Path,
        typer.Option("--experiment-root", "-o", help="Local experiment artifact directory."),
    ],
    candidates: Annotated[
        list[str] | None,
        typer.Option("--candidate", help="Adapter name. Repeatable."),
    ] = None,
    sample_rows: Annotated[int, typer.Option("--sample-rows", min=1)] = 1_000,
    fit_seed: Annotated[str, typer.Option("--fit-seed")] = "fit-0",
    evaluation_seed: Annotated[str, typer.Option("--evaluation-seed")] = "evaluation-0",
    ctgan_epochs: Annotated[int, typer.Option("--ctgan-epochs", min=1)] = 300,
    gmm_components: Annotated[int, typer.Option("--gmm-components", min=1, max=64)] = 5,
    tensorflow_epochs: Annotated[int, typer.Option("--tensorflow-epochs", min=1)] = 100,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Run an experimental single-table candidate tournament."""

    dataset = DatasetContract.model_validate_json(contract_path.read_text(encoding="utf-8"))
    names = candidates or ["empirical-independent"]
    hyperparameters = {
        "ctgan": {"epochs": ctgan_epochs},
        "sklearn-gaussian-mixture": {"n_components": gmm_components},
        "tensorflow-gan": {"epochs": tensorflow_epochs},
    }
    configurations = tuple(
        CandidateConfig(adapter_name=name, hyperparameters=hyperparameters.get(name, {}))
        for name in names
    )
    report = run_tournament(
        TournamentRequest(
            split_manifest_path=split_manifest_path,
            dataset_contract=dataset,
            experiment_root=experiment_root,
            candidates=configurations,
            sample_row_count=sample_rows,
            fit_seed=fit_seed,
            evaluation_seed=evaluation_seed,
            policy=EvaluationPolicy(),
            overwrite=overwrite,
        )
    )
    typer.echo(f"experiment_id: {report.experiment_id}")
    typer.echo(f"decision: {report.decision.value}")
    typer.echo(f"recommended_adapter: {report.recommended_adapter or '-'}")
    typer.echo(f"release_approved: {str(report.release_approved).lower()}")
    typer.echo(f"report: {experiment_root / 'tournament-report.json'}")


if __name__ == "__main__":
    app()
