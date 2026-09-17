## Why

DataBoom has documented a sound statistical and ML strategy but cannot yet fit,
sample, compare, or govern a source-trained model. The next backend milestone is
to make a GAN a real, measurable candidate without letting neural complexity,
dependency licensing, or training failures compromise the deterministic product.

## What Changes

- Add web-safe, versioned contracts for tabular dataset splits, synthesizer
  capabilities, model lineage, quality results, and candidate decisions.
- Add deterministic streaming train/validation/holdout splitting, including a
  group-preserving mode that prevents one subject from crossing partitions.
- Add a provider-neutral adapter registry, an independent empirical baseline,
  and an optional scikit-learn Gaussian-mixture baseline for joint structure.
- Add an optional CTGAN adapter that imports its ML stack only inside the worker
  process, records dependency/license metadata, and never loads during FastAPI
  startup.
- Add an owned optional TensorFlow GAN adapter with a data-only Keras generator
  artifact, deterministic feature transforms, and the same tournament gates.
- Add a first candidate tournament that samples every eligible adapter with a
  fixed evaluation seed and reports fidelity, diversity, exact-copy risk,
  runtime, and reproducibility evidence separately.
- Add a dedicated ML worker CLI and local JSON/CSV model and report artifacts.
- Update the architecture, quality, roadmap, operations, research, and
  understanding documents with primary-paper links and honest readiness limits.
- Remove the superseded repository-level `instructions.md`; `AGENTS.md`, stable
  docs, and OpenSpec become the durable guidance and task-contract surfaces.
- **License boundary:** TensorFlow and scikit-learn use permissive provider
  licenses, while the maintained `ctgan` package is an optional provider
  dependency subject to its own BUSL-1.1 terms. DataBoom's core contracts,
  baseline, evaluation, and tournament remain independent of that package.

### Non-goals

- No frontend work or public training API in this change.
- No multi-table, temporal, graph-native, diffusion, or differentially private
  neural model in this first slice.
- No claim that CTGAN, the TensorFlow GAN, or a scikit-learn model is promoted,
  privacy-safe, anonymous, or production-ready merely because training
  completes.
- No loading of untrusted model artifacts and no model training in the FastAPI
  process.

## Capabilities

### New Capabilities

- `dataset-partitioning`: Deterministic row or group-preserving split artifacts,
  fingerprints, and leakage checks for source-trained evaluation.
- `synthesizer-adapters`: Provider-neutral capabilities, model lineage, an
  empirical baseline, an optional scikit-learn mixture baseline, and optional
  lazily loaded CTGAN and TensorFlow GAN adapters.
- `candidate-tournament`: Fixed-seed sampling, quality and privacy diagnostics,
  hard-gate decisions, and experimental recommendations without automatic
  production promotion.

### Modified Capabilities

None. This is the first OpenSpec capability baseline in the repository.

## Impact

- New `databoom.synthesis` backend package and ML worker CLI.
- New optional dependency groups for scikit-learn, TensorFlow CPU, and the CTGAN
  provider.
- New local split, model, sample, experiment, and report artifacts.
- New unit and integration tests for partition leakage, adapter isolation,
  lineage checksums, metric behavior, and tournament decisions.
- Documentation ownership moves away from `instructions.md` to `AGENTS.md`,
  `docs/`, `understanding.md`, and archived OpenSpec changes.
