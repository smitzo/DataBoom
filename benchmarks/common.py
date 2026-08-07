"""Shared helpers for local benchmark scripts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def prepare_output_dir(output_dir: Path, *, overwrite: bool) -> None:
    """Create or clear a benchmark output directory."""

    if output_dir.exists() and overwrite:
        shutil.rmtree(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)


def directory_size(path: Path) -> int:
    """Return recursive file size for an artifact directory."""

    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def write_metrics(output_dir: Path, metrics: dict[str, Any]) -> None:
    """Write metrics to disk and stdout in the same format."""

    metrics_path = output_dir / "metrics.json"
    rendered_metrics = json.dumps(metrics, indent=2)
    metrics_path.write_text(rendered_metrics, encoding="utf-8")
    print(rendered_metrics)
