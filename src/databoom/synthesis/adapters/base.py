"""Provider-neutral adapter protocol and capability registry."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from databoom.synthesis.contracts import (
    DatasetContract,
    FitConfig,
    ModelManifest,
    SampleArtifact,
    SynthesizerCapabilities,
)


class SynthesizerUnavailableError(RuntimeError):
    """Raised when an optional provider is not runnable in the active worker."""


class SynthesizerAdapter(Protocol):
    """Interface implemented by every single-table candidate."""

    @property
    def capabilities(self) -> SynthesizerCapabilities: ...

    def fit(
        self,
        training_csv: Path,
        dataset: DatasetContract,
        experiment_root: Path,
        model_dir: Path,
        config: FitConfig,
    ) -> ModelManifest: ...

    def sample(
        self,
        manifest: ModelManifest,
        experiment_root: Path,
        output_path: Path,
        *,
        row_count: int,
        seed: str,
    ) -> SampleArtifact: ...


class AdapterRegistry:
    """Small explicit registry that prevents product-name model branches."""

    def __init__(self) -> None:
        self._adapters: dict[str, SynthesizerAdapter] = {}

    def register(self, adapter: SynthesizerAdapter) -> None:
        name = adapter.capabilities.name
        if name in self._adapters:
            raise ValueError(f"synthesizer adapter already registered: {name}")
        self._adapters[name] = adapter

    def get(self, name: str) -> SynthesizerAdapter:
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise KeyError(f"unknown synthesizer adapter: {name}") from exc

    def capabilities(self) -> tuple[SynthesizerCapabilities, ...]:
        return tuple(self._adapters[name].capabilities for name in sorted(self._adapters))


def build_default_registry() -> AdapterRegistry:
    """Build the default registry without importing optional training libraries."""

    from databoom.synthesis.adapters.ctgan import CtganAdapter
    from databoom.synthesis.adapters.empirical import IndependentEmpiricalAdapter
    from databoom.synthesis.adapters.gaussian_copula import GaussianCopulaAdapter
    from databoom.synthesis.adapters.sklearn_gmm import SklearnGaussianMixtureAdapter
    from databoom.synthesis.adapters.tensorflow_gan import TensorflowGanAdapter

    registry = AdapterRegistry()
    registry.register(IndependentEmpiricalAdapter())
    registry.register(GaussianCopulaAdapter())
    registry.register(SklearnGaussianMixtureAdapter())
    registry.register(TensorflowGanAdapter())
    registry.register(CtganAdapter())
    return registry
