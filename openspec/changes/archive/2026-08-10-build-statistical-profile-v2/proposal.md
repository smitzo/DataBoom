## Why

The candidate tournament can split, fit, sample, and report basic direct metrics,
but it has no reusable statistical profile contract or reviewed quality intent.
Without versioned profile evidence, later copula models, privacy diagnostics, and
promotion calibration would each invent incompatible summaries and fingerprints.

## What Changes

- Add web-safe `DataQualityIntent` and statistical Profile v2 contracts.
- Add deterministic, bounded-memory CSV profiling based on a hash-priority sample
  plus exact source, row-count, and per-column missingness evidence.
- Report numeric quantiles, histograms, skew, Tukey-tail rates, categorical
  frequencies, missingness patterns, and pairwise dependency summaries.
- Write checksummed Profile v2 JSON artifacts through a dedicated worker command.
- Add training, holdout, and synthetic profile lineage to tournament artifacts
  without changing the experimental non-promotion boundary.
- Update quality, architecture, roadmap, operations, and decision documentation.

### Non-goals

- No Gaussian copula, new neural provider, frontend, or public profiling API.
- No claim that a profile or distance diagnostic proves anonymity or privacy.
- No differential privacy, membership inference, attribute inference, or
  production release threshold in this change.
- No pandas, NumPy, scikit-learn, TensorFlow, torch, or CTGAN dependency in the
  profiler or FastAPI process.
- No exact unbounded categorical cardinality structure in memory; high-cardinality
  summaries are explicitly sample-based and report their coverage.

## Capabilities

### New Capabilities

- `statistical-profile`: Versioned quality intent, bounded deterministic source
  summaries, dependency evidence, checksummed artifacts, and worker CLI support.

### Modified Capabilities

- `candidate-tournament`: Record reusable training, holdout, and synthetic Profile
  v2 artifact lineage alongside direct metric and gate evidence.

## Impact

- Extends `databoom.synthesis` contracts and worker CLI without adding base
  dependencies.
- Adds a standard-library CSV profiler and Profile v2 JSON artifacts beneath the
  local experiment root.
- Extends tournament reports and candidate results with relative profile paths.
- Adds controlled statistical fixtures and focused contract, computation,
  artifact-integrity, CLI, and tournament tests.
