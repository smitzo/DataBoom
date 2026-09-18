# Quality Evaluation and Benchmarks

This document defines how DataBoom measures synthetic data quality, selects
benchmark datasets, compares model candidates, and decides whether an output may
be released. It is the verification companion to the
[Statistical and ML Synthesis Architecture](statistical-synthesis-architecture.md).

## Current Implemented Evidence

The first experimental single-table tournament now implements a deliberately
small, inspectable subset of this policy:

- deterministic row-hash and subject/group-preserving train, validation, and
  holdout CSV artifacts with SHA-256 fingerprints,
- versioned quality intent and Profile v2 evidence with exact row/null counts,
  deterministic bounded samples, quantiles, histograms, skew, Tukey-tail rates,
  categorical coverage, missingness patterns, and pairwise dependencies,
- an owned independent empirical baseline, optional scikit-learn
  Gaussian-mixture baseline, owned optional TensorFlow GAN, and optional CTGAN
  provider,
- exact contract/column checks, sample row counts, numeric parsing, and required
  null checks,
- numeric Kolmogorov-Smirnov and normalized mean error,
- categorical total-variation distance,
- whole-row synthetic uniqueness and exact training-row match rate,
- fit/sample wall time and repeat-sample checksum evidence,
- independent structural, fidelity, diversity, exact-copy privacy, and
  reproducibility gates,
- shared training/holdout Profile v2 lineage plus a synthetic profile for each
  completed candidate,
- a permanent `release_approved=false` decision while production evidence is incomplete.

The implementation does not yet use Profile v2 quantiles, tails, or dependencies
as calibrated promotion gates. Downstream utility, near-neighbor privacy,
membership or attribute inference, formal DP, peak resource use, and calibrated
release thresholds also remain incomplete. The full research mapping and
limitations are in
[Neural Synthesis Research](neural-synthesis-research.md).

## Quality Is Multidimensional

There is no honest universal synthetic-data accuracy score. A dataset can match
every column histogram while destroying correlations. It can train a useful
classifier while copying source records. It can preserve relationships while
missing rare but important cases.

DataBoom therefore evaluates independent dimensions:

1. structural validity,
2. univariate fidelity,
3. pairwise and joint fidelity,
4. diversity and coverage,
5. relational, temporal, or graph coherence,
6. downstream utility,
7. privacy risk,
8. runtime and resource efficiency,
9. reproducibility and operational completeness.

A report must show the dimensions separately before presenting any weighted
summary. A green average must never hide a failed hard gate.

## Evaluation Dataset Split

Source-trained evaluation requires three disjoint partitions:

- **training** fits candidate synthesizers,
- **validation** tunes hyperparameters and chooses among candidates,
- **holdout** provides the final comparison and is evaluated once per promoted
  candidate version.

Default starting split: 70/15/15, adjusted for dataset size and domain needs.
Splits should be stratified by important targets and grouped by subject for
linked or temporal data. Events from one person, account, device, or graph must
not leak across partitions.

For time-dependent use cases, use chronological splits instead of random splits.
For graph collections, split whole graphs where possible. For one large graph,
the evaluation protocol must declare which nodes, edges, time windows, or
subgraphs are hidden.

## Metric Families

### 1. Structural Validity

Hard checks:

- schema and data-type conformance,
- required-field completion,
- primary and unique key validity,
- foreign-key and graph endpoint integrity,
- document shape and reference consistency,
- configured row, document, node, and edge counts,
- allowed ranges and enumerations,
- business constraints expressed in the approved plan.

Default release gate: 100% for declared hard constraints. Statistical realism
cannot compensate for an orphaned foreign key or impossible value.

### 2. Univariate Fidelity

Continuous and ordinal columns:

- Kolmogorov-Smirnov statistic,
- Wasserstein distance normalized by robust source scale,
- quantile error at configured percentiles,
- mean, variance, skewness, and tail error,
- zero, null, and outlier rate error.

Categorical and boolean columns:

- total variation distance,
- Jensen-Shannon divergence,
- frequent and rare category coverage,
- null and unknown-category rate.

Datetime columns:

- interval and quantile error,
- weekday, month, hour, and seasonal distribution distance,
- event-gap distribution where order matters.

No metric should compare raw numeric scales without normalization. Large-unit
columns would otherwise dominate a weighted score.

### 3. Pairwise and Joint Fidelity

- Pearson and Spearman correlation delta,
- Cramer's V or contingency-table distance for categorical pairs,
- mutual-information difference for mixed and non-linear dependencies,
- conditional distribution distance for declared column groups,
- missingness-pattern distance,
- classifier two-sample test as a diagnostic,
- alpha-precision for fidelity,
- beta-recall for coverage,
- authenticity for generalization rather than copying.

Pairwise metrics remain incomplete for high-dimensional interactions. Downstream
utility and sample-level metrics provide additional evidence.

### 4. Diversity and Rare Cases

- synthetic uniqueness after excluding intentional keys,
- duplicate and near-duplicate rates,
- support and cluster coverage,
- rare-category recall,
- tail-event recall and precision,
- distance distribution within synthetic data,
- mode-collapse indicators.

Rare events require minimum sample counts before a percentage is treated as
stable. The report should show confidence intervals or an insufficient-evidence
state for tiny groups.

### 5. Relational Coherence

- orphan and invalid-key counts,
- parent-child fanout distance,
- zero-child parent rate,
- child-count distributions conditioned on parent segment,
- cross-table correlation and conditional distribution error,
- join-result row counts and aggregate query error,
- linked event sequence-length and transition error.

DataBoom should keep a small suite of canonical SQL queries per benchmark. Query
result similarity tests the behavior users actually see after joining tables.

### 6. Document Coherence

- required and optional path presence,
- nested object and array-length distributions,
- reference integrity,
- type stability per path,
- co-occurrence of nested fields,
- flattened-path distribution and dependency metrics,
- semantic checks for configured text fields.

Document evaluation must distinguish an absent field from a field present with
`null`; many document databases and applications treat them differently.

### 7. Temporal Coherence

- autocorrelation error at configured lags,
- transition-matrix distance,
- sequence length and event-gap distance,
- trend and seasonal decomposition similarity,
- ordering and monotonic timestamp validity,
- forecasting or sequence-classification train-synthetic/test-real utility.

Matching a timestamp range without these checks is not time-series fidelity.

### 8. Graph Coherence

- in-degree and out-degree distribution distance,
- connected-component count and size distance,
- clustering coefficient distribution,
- shortest-path sample distribution,
- community-size and modularity difference,
- assortativity and attribute mixing,
- graph statistic maximum mean discrepancy,
- downstream node, edge, or graph task utility where labels exist.

Graph-Boom should evaluate each edge type separately as well as the complete
graph. A globally plausible graph can still contain an unrealistic relation.

### 9. Downstream Utility

Where a target task exists, compare:

- train real, test holdout real: utility ceiling,
- train synthetic, test holdout real: synthetic replacement utility,
- train real plus synthetic, test holdout real: augmentation utility,
- train real, test synthetic: diagnostic only, not a replacement score.

Tasks may include classification, regression, forecasting, anomaly detection,
aggregate SQL analysis, or graph prediction. Models, preprocessing, seeds, and
hyperparameter budgets must be identical across candidates.

Utility is use-case-specific. Strong classification utility does not prove
accurate aggregates, rare groups, privacy, or another target task.

### 10. Privacy Risk

Empirical privacy checks:

- exact source-row matches after excluding intentional reference data,
- nearest-neighbor and distance-to-closest-record distributions,
- nearest-neighbor distance ratio,
- train-versus-holdout distance comparison,
- rare combination exposure,
- membership-inference attack success,
- attribute-inference tests for high-risk releases.

Formal privacy checks:

- verify that a declared differentially private mechanism is implemented,
- record epsilon, delta, clipping, accounting method, and composition,
- reject labels such as "anonymous" or "privacy-safe" based only on distance
  metrics.

NIST guidance is explicit that non-differentially-private synthetic methods
generally provide only informal privacy guarantees. DataBoom should report the
actual mechanism and evidence rather than infer safety from the word synthetic.

### 11. Performance and Operations

- profile time and memory,
- model fit time and peak memory,
- sample throughput and peak memory,
- quality-report time,
- artifact size and model size,
- CPU/GPU type and cost estimate,
- cold and warm latency,
- deterministic rerun equality where supported,
- failure, retry, and cancellation behavior.

Quality improvements that make the selected deployment impossible are not
production improvements.

## Quality Report Contract

A future report should have this shape:

```json
{
  "report_version": "1",
  "mode": "source_faithful",
  "profile_id": "profile_...",
  "model_id": "model_...",
  "dataset_fingerprint": "sha256:...",
  "split_strategy": "grouped_subject_70_15_15",
  "hard_gates": {
    "structural_validity": "passed",
    "privacy_policy": "passed",
    "operational_completeness": "passed"
  },
  "dimensions": {
    "univariate": {"score": 0.94, "status": "passed"},
    "joint": {"score": 0.88, "status": "passed"},
    "coverage": {"score": 0.91, "status": "passed"},
    "utility": {"score": 0.86, "status": "passed"},
    "privacy": {"status": "empirically_audited"}
  },
  "performance": {
    "fit_seconds": 42.8,
    "sample_rows_per_second": 18000,
    "peak_memory_mb": 782
  },
  "decision": "approved",
  "warnings": []
}
```

The example values are illustrative, not current DataBoom benchmark results.

## Candidate Tournament

For each eligible dataset:

1. fingerprint and split the source,
2. build the profile from training data only,
3. fit the deterministic/statistical baseline,
4. fit eligible mixture and neural candidates with equal tuning budgets,
5. sample the same number of rows with fixed evaluation seeds,
6. run hard validation and privacy checks,
7. calculate quality dimensions against untouched holdout data,
8. measure fit, sample, memory, and report costs,
9. rank only candidates that pass every hard gate,
10. select the simplest candidate on the quality-cost Pareto frontier,
11. persist the complete experiment manifest.

A candidate is not promoted because a paper or competitor uses it. It is
promoted because it improves DataBoom's measured workload.

## Initial Acceptance Policy

Exact thresholds must be calibrated from benchmark evidence. Until calibration,
the policy structure is:

| Gate | Initial policy |
| --- | --- |
| Structural validity | 100% of declared hard constraints. |
| Referential integrity | Zero orphaned references. |
| Plan compliance | All reviewed row, segment, and scenario targets within declared tolerances. |
| Privacy | Pass configured empirical tests; DP claims require a verified DP adapter and budget. |
| Fidelity | No critical column or declared dependency may fail its metric threshold. |
| Utility | Meet the use-case-specific minimum relative to the real-data ceiling. |
| Performance | Remain within configured fit, sample, memory, and cost budgets. |
| Reproducibility | Same seed and artifact versions reproduce supported deterministic outputs. |
| Evidence | Complete profile, experiment, quality, privacy, and lineage metadata. |

Weighted summary scores are allowed only after the table above passes. Thresholds
must be versioned by profile and use case. DataBoom should not market one global
"95% realistic" number.

## Benchmark Suite

The suite combines controlled ground truth with public, domain-relevant data.
Public datasets are not copied into the repository unless their licenses permit
it. Download scripts should verify version and checksum.

### Controlled Statistical Fixtures

Purpose: test whether metrics and synthesizers recover known truth.

Build generated fixtures for:

- correlated Gaussian and non-Gaussian variables,
- two- and three-component clusters,
- imbalanced categories,
- zero-inflated and sparse features,
- heavy tails and controlled outlier rates,
- MCAR and conditional missingness,
- seasonal event streams,
- relational parent/child segments,
- explicit international population mixtures.

Because the true distribution is known, these fixtures catch errors that a
single real dataset may hide.

### UCI Covertype

Purpose:

- large mixed tabular workload,
- continuous and binary features,
- multiclass utility,
- more than 500k rows for scale evidence.

Primary source: [UCI Covertype](https://archive.ics.uci.edu/dataset/31/covertype).

### UCI Bank Marketing

Purpose:

- mixed categorical and numeric columns,
- imbalanced target,
- conditional relationships and rare-category behavior,
- classification utility.

Primary source: [UCI Bank Marketing](https://archive.ics.uci.edu/dataset/222/bank+marketing).

### TPC-H

Purpose:

- normalized multi-table schema,
- key integrity and fanout,
- scale factors,
- aggregate and join-query fidelity,
- streaming generation performance.

TPC-H is a decision-support benchmark, not proof of human or domain realism. Use
its schema and query workload alongside controlled injected distributions.

Primary source: [TPC-H](https://www.tpc.org/tpch/).

### MIMIC-IV Demo

Purpose:

- healthcare-shaped relational and event data,
- subject-grouped evaluation,
- temporal and cross-table coherence,
- realistic missingness and coded categories.

Use only the openly available demo for automated work. Full MIMIC access has
credentialing and data-use requirements and must never become a CI dependency.

Primary source: [MIMIC-IV Clinical Database Demo](https://physionet.org/content/mimic-iv-demo/2.2/).

### UCR and UEA Time-Series Archives

Purpose:

- sequence classification utility,
- autocorrelation and temporal-shape metrics,
- varied sequence lengths and domains.

Primary sources:

- [UCR Time Series Classification Archive](https://www.cs.ucr.edu/~eamonn/time_series_data_2018/)
- [UEA Multivariate Time Series Archive](https://www.timeseriesclassification.com/)

### Stanford SNAP Graphs

Purpose:

- degree, component, community, and path metrics,
- directed, undirected, temporal, and attributed graph cases,
- small smoke datasets and larger performance datasets.

Start with one modest network suitable for CI and keep larger networks in
scheduled benchmarks.

Primary source: [Stanford Large Network Dataset Collection](https://snap.stanford.edu/data/).

### DataBoom Domain and Locale Fixtures

Purpose:

- stable regression tests for use cases not covered by public benchmarks,
- coherent `en-IN`, `en-US`, and weighted international populations,
- banking, healthcare, ecommerce, and SaaS constraints,
- scenario-controlled failures, sparsity, clusters, and rare events.

These fixtures must use fictional data and known generation parameters. They are
quality test cases, not evidence that the engine learned a real population.

## Benchmark Matrix

| Shape | Dataset | Primary evidence |
| --- | --- | --- |
| Controlled tabular | DataBoom statistical fixtures | Parameter recovery, metric correctness, determinism. |
| Large single table | UCI Covertype | Fidelity, multiclass utility, 500k scale. |
| Imbalanced mixed table | UCI Bank Marketing | Rare categories, conditional fidelity, utility. |
| Multi-table relational | TPC-H plus injected scenarios | Keys, fanout, joins, aggregates, throughput. |
| Healthcare events | MIMIC-IV demo | Subject grouping, missingness, temporal and relational coherence. |
| Time series | UCR/UEA selections | Autocorrelation, shape, forecasting/classification utility. |
| Graph | SNAP selections | Degree, community, paths, graph utility, scale. |
| International scenarios | DataBoom locale fixtures | Segment weights and cross-field geographic consistency. |

## Benchmark Tiers

### Pull Request Tier

- controlled fixtures,
- small TPC-H scale or equivalent relational fixture,
- one small temporal fixture,
- one small graph fixture,
- deterministic and metric-unit tests,
- target runtime under ten minutes on CPU.

### Nightly Tier

- UCI benchmark candidates,
- larger relational scale,
- repeated seeds,
- model tournament smoke runs,
- privacy and duplicate diagnostics,
- regression comparison to last accepted baseline.

### Release Tier

- complete benchmark matrix,
- 500k and 1M performance paths where applicable,
- multiple seeds with confidence intervals,
- CPU and configured GPU workers,
- full privacy policy,
- artifact and model lineage verification,
- signed benchmark manifest.

## Experiment Reproducibility

Every benchmark record should contain:

- dataset name, source URL, license, version, and checksum,
- split algorithm and seed,
- feature and relationship metadata,
- model adapter and code revision,
- hyperparameters and training seed,
- metric implementation versions,
- hardware, operating system, Python, and dependency versions,
- wall time, CPU/GPU time, peak memory, and artifact sizes,
- raw metric output and release decision.

Benchmark reports should never contain source rows or secrets.

## Expected Outcomes

After Quality Stages 0-2, DataBoom should be able to:

- describe source distributions beyond min/max,
- reproduce configured clusters, sparsity, missingness, and outlier rates,
- preserve important single-table and cross-table dependencies,
- generate explicit international population mixtures,
- compare generated output against source and holdout evidence,
- explain why a candidate passed or failed.

After Quality Stages 3-5, DataBoom should be able to:

- select between statistical, mixture, and optional neural candidates,
- train and sample complex tabular, relational, temporal, and graph shapes,
- evaluate utility for a declared downstream task,
- audit empirical privacy risk and support formal DP where configured,
- operate model training and sampling through production workers and lineage.

It should not promise:

- perfect replication of every hidden business rule,
- one model that is best for every dataset,
- privacy merely because output is synthetic,
- source fidelity when no source rows or distribution summaries were supplied,
- a universal quality percentage independent of the use case.

## Delivery Checklist

- [x] Add versioned profile v2 models.
- [x] Add deterministic row and grouped split utilities with fingerprints.
- [ ] Add chronological split utilities.
- [x] Add the first metric and quality report contract.
- [x] Add controlled statistical fixtures.
- [x] Implement first univariate numeric and categorical metrics.
- [ ] Implement pairwise and joint metrics.
- [x] Implement first pairwise Profile v2 dependency summaries.
- [ ] Implement relational and temporal metrics.
- [ ] Complete empirical privacy diagnostics beyond exact-row matches.
- [x] Add the independent empirical baseline synthesizer.
- [x] Add an experimental scikit-learn Gaussian-mixture candidate.
- [x] Add an owned experimental TensorFlow GAN candidate.
- [x] Add the optional CTGAN provider candidate.
- [x] Add the local experimental candidate tournament runner.
- [ ] Add public dataset download manifests.
- [ ] Add PR, nightly, and release benchmark jobs.
- [ ] Calibrate and version acceptance thresholds from measured evidence.
