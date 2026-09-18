# Statistical and ML Synthesis Architecture

This document defines how DataBoom should evolve from deterministic,
profile-guided generation into a measured statistical and machine-learning
synthesis platform. It owns model selection, profile contracts, generation
modes, and the boundary between planning and execution.

Quality metrics, benchmark datasets, experiment procedure, and release gates
are owned by [Quality Evaluation and Benchmarks](quality-evaluation-and-benchmarks.md).
Delivery status remains in the [Engineering Roadmap](roadmap.md).

## Executive Decision

DataBoom will not choose one model and call it universal. Structured data can be
single-table, relational, sparse, clustered, temporal, graph-shaped, textual, or
a mixture of those forms. Each shape has different failure modes.

DataBoom will use a **model portfolio with a measurable promotion policy**:

1. deterministic generation is the always-available baseline,
2. statistical models are the first source-trained synthesis layer,
3. conditional and mixture models handle multimodality, sparsity, and outliers,
4. neural models are optional candidates for difficult joint distributions,
5. temporal and graph models are selected only for their native data shapes,
6. every candidate must beat simpler baselines on a holdout quality report,
   while meeting privacy, latency, memory, and reproducibility budgets.

This is deliberately different from selecting the most sophisticated model by
default. A more complex model can train longer, cost more, memorize records, or
produce worse data on a small or simple dataset.

## Current Baseline And Experimental Candidate Path

DataBoom's production generation path remains deterministic and profile-guided.
Its present source-profile path
collects:

- row count,
- null count and null rate,
- distinct count,
- minimum and maximum values,
- frequent values,
- relationship fanout counts and histograms.

The generator currently uses those hints for null sampling, weighted frequent
categorical values, numeric and datetime ranges, and relationship fanout. It
also uses deterministic domain providers and row contexts to keep related
identity and locality fields coherent.

This is a useful deterministic and profile-guided production baseline. It is not yet a
joint-distribution learner. It does not currently learn mean, variance,
quantiles, covariance, clusters, rare tails, multivariate outliers, seasonality,
or cross-table conditional distributions.

An experimental single-table source-trained path now exists under
`databoom.synthesis`:

- deterministic row-hash or group-preserving train/validation/holdout splitting,
- explicit dataset contracts whose columns are restricted from training by default,
- versioned `DataQualityIntent` and Profile v2 artifacts with exact source and
  missingness evidence plus bounded deterministic distribution summaries,
- an owned independent empirical candidate,
- an owned standard-library Gaussian-copula candidate with bounded empirical
  marginals and explicit nullable indicators,
- an optional lazily imported scikit-learn Gaussian-mixture candidate with a
  data-only JSON artifact,
- an owned optional TensorFlow GAN with a Keras v3 generator artifact,
- an optional lazily imported CTGAN provider with an explicit license boundary,
- provider-neutral capability and model-lineage manifests,
- structural, numeric, categorical, diversity, exact-copy, performance, and
  reproducibility evidence,
- a local candidate tournament that can recommend further controlled evaluation
  but can never approve a production release, with shared training/holdout
  profiles and a separate synthetic profile for each completed candidate.

This is the first executable Q0-Q3 vertical slice, not completion of those
quality stages. The copula, Gaussian mixture, and GANs can model joint structure,
but calibrated joint metrics, utility evaluation, privacy attacks, calibrated
thresholds, signed lineage, and hardened worker isolation remain required. The
implementation and paper-by-paper rationale are documented in
[Neural Synthesis Research](neural-synthesis-research.md).

## Two Product Modes

DataBoom must distinguish these modes in APIs, reports, and product wording.

### Scenario-Faithful Mode

Inputs:

- schema or document/graph contract,
- domain and locale intent,
- declarative distributions and constraints,
- optional reviewed LLM plan,
- no source rows required.

Promise:

- valid, coherent, configurable test data,
- reproducible edge cases and population scenarios,
- no claim that output reproduces an unknown production distribution.

Best uses:

- application development,
- deterministic CI fixtures,
- demos,
- load tests,
- explicit rare-event and failure-path testing.

### Source-Faithful Mode

Inputs:

- schema plus approved source rows or privacy-safe feature summaries,
- train, validation, and holdout partitions,
- declared utility and privacy objectives.

Promise:

- measured approximation of selected source properties,
- reportable distribution, dependency, utility, and privacy metrics,
- no unconditional claim of perfect fidelity or anonymity.

Best uses:

- analytics development,
- model training experiments,
- realistic staging datasets,
- data sharing after the required privacy controls are satisfied.

Source-faithful mode introduces training, model artifacts, privacy review, and
compute costs. Those costs must never silently enter the lightweight
scenario-faithful workflow.

## End-to-End Architecture

```mermaid
flowchart LR
    Input[Schema, Source, or Intent] --> Classifier[Data Shape Classifier]
    Classifier --> Profiler[Statistical Profiler]
    Profiler --> Profile[Versioned Profile IR]
    Input --> Planner[Planner and Constraint Resolver]
    Profile --> Planner
    Planner --> Intent[Reviewed Quality Intent]
    Intent --> Selector[Model Candidate Selector]
    Profile --> Selector
    Selector --> Train[Candidate Fit and Tune]
    Train --> Registry[Model and Profile Registry]
    Registry --> Sample[Deterministic Sampling Runtime]
    Sample --> Enforce[Constraint and Relationship Enforcement]
    Enforce --> Export[Streaming Export]
    Export --> Evaluate[Quality and Privacy Evaluation]
    Evaluate --> Gate{Acceptance Gate}
    Gate -->|Pass| Release[Approved Dataset]
    Gate -->|Fail| Selector
```

The planner converts user intent into a strict contract. It does not write bulk
rows. The selector proposes candidate synthesizers. The evaluation service, not
the LLM and not the model name, decides whether a candidate is acceptable.

## Core Contracts

### `DataQualityIntent`

The generation plan needs a structured quality section rather than prose-only
notes. A future contract should express:

```yaml
mode: source_faithful
population:
  segments:
    - locale: en-IN
      weight: 0.55
    - locale: en-US
      weight: 0.45
distribution_goals:
  clusters:
    column_group: [annual_income, account_balance, customer_tier]
    preserve: true
  sparsity:
    column: secondary_phone
    target_zero_or_null_rate: 0.72
  outliers:
    column: transaction_amount
    target_rate: 0.008
    tail: upper
  correlations:
    - columns: [account_age_months, credit_limit]
      direction: positive
      tolerance: 0.08
utility:
  task: churn_classification
privacy:
  policy: empirical_audit
reproducibility:
  seed: 42
```

The exact Pydantic models will be designed during implementation. The important
boundary is that ambiguous natural language becomes reviewed, typed intent
before selection or generation begins.

### `StatisticalProfile`

The profile is a versioned intermediate representation shared by profilers,
model adapters, evaluators, and reports. It should contain no more raw samples
than the configured privacy policy allows.

Per-column statistics:

- semantic and storage type,
- count, null rate, zero rate, and distinct rate,
- minimum, maximum, mean, variance, and standard deviation,
- quantiles and an adaptive histogram,
- skewness and excess kurtosis,
- frequent and rare category counts,
- string length and safe pattern summaries,
- datetime interval, calendar buckets, and seasonality hints,
- geographic and locale classification where explicitly configured.

Pairwise statistics:

- Pearson correlation for appropriate continuous variables,
- Spearman rank correlation for monotonic relationships,
- contingency tables or Cramer's V for categorical pairs,
- mutual information for non-linear mixed dependencies,
- conditional category and numeric summaries,
- missingness correlations and conditional missingness.

Table-level statistics:

- candidate cluster count and cluster weights,
- density and sparsity indicators,
- outlier scores and tail summaries,
- key uniqueness and functional dependencies,
- constraints that cannot be inferred safely.

Relationship-level statistics:

- parent-child fanout distribution,
- zero-child parent rate,
- child counts conditioned on parent segments,
- cross-table conditional summaries,
- event sequence length and ordering,
- temporal gaps between linked events.

Graph-level statistics:

- node and edge type counts,
- in-degree and out-degree distributions,
- connected components,
- clustering coefficients,
- path-length samples,
- community-size distribution,
- assortativity and attribute mixing where applicable.

### `SynthesizerAdapter`

Every model implementation should satisfy one provider-neutral interface:

```python
class SynthesizerAdapter(Protocol):
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
```

Capabilities must declare supported data shapes, conditional sampling,
determinism, CPU/GPU needs, incremental fitting, and privacy mechanisms. The
engine selects adapters by capability; API routes and product names must not
contain model-specific branches.

The current protocol implements the fit/sample subset needed for the first local
tournament. Cost estimation, conditional sampling, incremental fitting, model
registry lookup, and privacy-mechanism declarations are additive follow-up
contracts.

## Model Portfolio

### Level 0: Deterministic Rules and Contexts

Use when:

- no source data is available,
- CI reproducibility matters most,
- explicit edge cases are requested,
- the schema is simple or data volume is very large.

Techniques:

- seeded primitive providers,
- declarative categorical weights,
- context-dependent field generation,
- key and relationship solvers,
- explicit constraints and formulas,
- controlled error and outlier injection.

This remains the fallback even after ML is added. It is cheap, inspectable,
streamable, and reliable in offline deployments.

### Level 1: Empirical and Copula Models

Use when:

- source rows exist,
- the table is small or medium,
- explainability and CPU operation are important,
- dependencies are not extremely irregular.

Techniques:

- empirical categorical distributions,
- quantile or histogram sampling,
- parametric distribution fitting,
- kernel density estimation for selected continuous columns,
- Gaussian copulas for joint rank dependencies,
- bootstrapped residuals with duplicate controls.

This should be DataBoom's first source-trained implementation. It gives a strong,
fast baseline and makes profile and quality-report weaknesses visible before a
deep-learning dependency is introduced.

### Level 2: Conditional Mixtures

Use when:

- numeric data is multimodal or clustered,
- the population contains explicit subgroups,
- zeros and missing values are structural,
- rare tails must be represented deliberately.

Techniques:

- Gaussian or Bayesian mixture models,
- conditional probability tables,
- hurdle and zero-inflated models,
- body-and-tail models for heavy-tailed variables,
- segment-first generation followed by conditional columns,
- isolation or robust covariance methods for outlier characterization.

A sparse or outlier-rich dataset should not be produced by increasing generic
randomness. The plan should specify whether unusual values are noise, valid rare
events, a separate cluster, or an adversarial test scenario.

### Level 3: Neural Single-Table Models

Candidates:

- conditional tabular GANs and tabular variational autoencoders,
- mixed-type diffusion models,
- latent-space tabular diffusion models.

Use when:

- the source has enough rows to learn a complex joint distribution,
- simpler candidates fail measured joint or downstream utility gates,
- training cost and model governance are acceptable.

Conditional tabular GAN research introduced mode-specific normalization and
training-by-sampling for mixed data and imbalanced categories. More recent
diffusion approaches report strong results for heterogeneous tabular data. Those
results justify candidates, not automatic selection. Each candidate still must
beat DataBoom's own statistical baseline on the customer's holdout and utility
task.

### Level 4: Relational and Sequential Models

Relational synthesis must preserve more than foreign keys. It must preserve how
child rows depend on their subject and on prior events.

DataBoom should use a subject-first strategy:

1. identify subject or root tables,
2. train or configure one model per table,
3. pass selected parent context into linked-table models,
4. model child cardinality before child values,
5. preserve temporal order for event tables,
6. solve remaining non-context foreign keys for integrity,
7. evaluate both cross-table statistics and downstream joins.

For temporal data, begin with empirical transition matrices, seasonal
distributions, and block/bootstrap baselines. Add learned sequence models only
when autocorrelation, transition, and forecasting metrics demonstrate a gain.

Flattening a multi-table database into one giant table is not the default. It
causes row multiplication, sparse columns, information leakage between entities,
and difficult reconstruction of cardinalities.

### Level 5: Graph Models

Graph-Boom should begin with interpretable graph families:

- configuration models for degree distributions,
- stochastic block models for communities,
- preferential attachment where the domain supports it,
- explicit edge-type and cardinality rules.

Autoregressive or graph neural generators become candidates when a source
contains enough graph structure and simpler families fail degree, community,
path, or downstream graph-task gates. Graph quality is not measured with table
correlation alone.

### Level 6: Unstructured Text

An LLM may generate free-text fields such as notes, descriptions, or support
messages. It must be conditioned on the already generated structured row context
and constrained by schema, safety, privacy, and length rules.

LLMs should not generate the numeric, categorical, key, or relationship core of
a million-row dataset. Text generation should be optional, batched, cached where
safe, and replaceable with templates for offline or low-cost runs.

## Model Selection Policy

The selector should produce a ranked candidate set, not an irreversible answer.

Inputs:

- data shape and product kind,
- row and column counts,
- type and cardinality profile,
- multimodality, sparsity, tail, and dependency indicators,
- relational depth or graph topology,
- requested conditional controls,
- CPU/GPU, latency, memory, and cost budgets,
- privacy policy,
- required reproducibility.

Selection rules:

1. Always include the deterministic baseline for scenario mode.
2. Always include an empirical or copula baseline for source mode.
3. Add a mixture candidate when multimodality or structural zeros are detected.
4. Add neural candidates only above configured data sufficiency thresholds.
5. Reject adapters that cannot represent the required data shape or conditions.
6. Fit candidates on training data and tune on validation data.
7. Evaluate once on untouched holdout data.
8. Promote the simplest candidate that passes all hard gates and meets the
   weighted quality objective within resource budgets.

The LLM may explain these choices, but it must not override failed metrics.

## International and Diverse Populations

International generation should use an explicit population mixture. A locale
controls linguistic and formatting conventions such as names, addresses, phone
numbers, dates, and postal codes. It is not a safe proxy for ethnicity, religion,
citizenship, or other protected traits.

Rules:

- use customer-provided country/locale weights when available,
- learn weights from a source profile only when policy permits,
- ask for review when the requested population is ambiguous,
- generate country first, then region, city, postcode, phone, currency, and
  timezone conditionally,
- preserve mixed-nationality and expatriate scenarios only through explicit
  rules or source evidence,
- report coverage by configured population segment,
- never invent protected-attribute distributions from stereotypes.

For a truly international customer base, a single locale is wrong and uniform
country sampling is usually wrong. The plan must contain a weighted mixture or a
documented scenario distribution.

## Missingness, Sparsity, Clusters, and Outliers

These properties require separate intent because they are not interchangeable.

### Missingness

- MCAR: missing independently at a configured rate.
- MAR: missing conditionally on observed fields.
- MNAR: missing according to an explicit domain rule that cannot be inferred
  safely from observed data alone.

### Sparsity

- use hurdle models for a zero/no-event decision followed by a value model,
- preserve sparse-vector density and active-feature counts,
- keep structural zero distinct from missing and measured zero.

### Clusters

- identify stable candidate segments with mixture models or domain labels,
- preserve cluster weights and within-cluster distributions,
- measure cluster coverage instead of only global mean and variance.

### Outliers and Tails

- distinguish data errors from valid rare events,
- model normal body and heavy tail separately when appropriate,
- expose an explicit outlier rate and tail direction in scenario mode,
- cap impossible values through domain constraints,
- evaluate rare-event recall and not just average distribution distance.

Mean and variance alone cannot represent these structures. Two datasets can
share both values while having different clusters, tails, dependencies, and
missingness mechanisms.

## Privacy Boundary

Synthetic data is not automatically anonymous. A model can memorize rare rows,
and a high-fidelity sample can be too close to a training subject.

Until Masker-Boom and privacy hardening are implemented, source-trained outputs
must be described as **empirically audited**, not formally private. Required
future controls include:

- exact and near-duplicate detection,
- distance-to-closest-record and nearest-neighbor ratio checks,
- train-versus-holdout distance comparisons,
- membership-inference tests for high-risk releases,
- rare-category protections,
- model and report access control,
- optional differentially private training with explicit epsilon/delta budgets.

Differential privacy is the formal mechanism in the portfolio. It introduces a
real utility tradeoff and belongs behind a reviewed policy, not a marketing
toggle.

## Reproducibility and Operations

Every source-trained run should persist:

- immutable profile version and data fingerprint,
- train/validation/holdout split fingerprints,
- quality intent and approved plan version,
- adapter name and implementation version,
- hyperparameters and seed,
- dependency and runtime image versions,
- fit and sample timings,
- resource use and model artifact checksum,
- complete quality and privacy report identifiers.

CPU statistical dependencies should be an optional `quality` extra. Neural and
GPU dependencies should live in separate optional extras or worker images. The
FastAPI web process must not import heavyweight training libraries during normal
API startup.

## Implementation Sequence

Current delivery is intentionally non-linear because the first vertical slice
implemented enough Q0 measurement and Q3 adapter plumbing to evaluate one Q1
baseline, one optional classical joint candidate, and two optional neural
candidates. This does not skip the remaining gates; it exposes them as explicit
incomplete evidence.

### Quality Stage 0: Contracts and Measurement

- add `DataQualityIntent` and versioned profile contracts, `implemented`
- collect bounded Profile v2 numeric, categorical, tail, missingness, and
  dependency statistics, `portable CSV baseline implemented`
- build holdout splitting and dataset fingerprints, `row and grouped split implemented`
- add quality report schemas and metric registry, `first report and metric set implemented`
- keep output unchanged while measurement stabilizes.

### Quality Stage 1: Statistical Synthesis

- implement empirical categorical and quantile sampling, `bounded independent empirical baseline implemented; quantile model pending`
- add Gaussian copula candidate, `owned bounded standard-library adapter implemented`
- add conditional missingness and datetime seasonality,
- compare generated output with source and holdout profiles,
- expose scenario-faithful versus source-faithful mode.

### Quality Stage 2: Mixtures and Controlled Populations

- add cluster and mixture candidates, `experimental Gaussian-mixture candidate implemented; controlled segment intent pending`
- add zero-inflated, sparse, and tail controls,
- implement explicit international population mixtures,
- add constraint DSL and conditional distribution controls,
- add rare-event coverage metrics.

### Quality Stage 3: Adapter Tournament

- implement model adapter and capability registry, `first fit/sample registry implemented`
- add conditional GAN/VAE candidates behind optional dependencies, `optional CTGAN provider and owned generic TensorFlow GAN implemented; conditional owned GAN and VAE pending`
- add diffusion candidates as experimental adapters,
- train candidates out of process, `local ML worker CLI implemented; hardened worker pending`
- promote models through benchmark and customer-specific gates, `experimental recommendation only`.

### Quality Stage 4: Native Complex Shapes

- add subject-first relational training,
- add temporal baseline and learned sequence candidates,
- add graph family and learned graph candidates,
- evaluate cross-table, sequence, and graph-native properties.

### Quality Stage 5: Privacy and Production Hardening

- add privacy attack suite and release policies,
- add optional differentially private adapters,
- persist model registry and lineage,
- support durable artifact and model storage,
- distribute training and sampling workers,
- establish drift monitoring and scheduled retraining.

## Research Basis

The architecture is informed by primary research rather than tied to a vendor:

- [CTGAN: Modeling Tabular Data using Conditional GAN](https://papers.neurips.cc/paper_files/paper/2019/hash/254ed7d2de3b23ab10936522dd547b78-Abstract.html)
- [TabDDPM: Modelling Tabular Data with Diffusion Models](https://proceedings.mlr.press/v202/kotelnikov23a.html)
- [TabSyn: Mixed-Type Tabular Data Synthesis with Score-based Diffusion](https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9750610639c3e7a849cff746bf60dbd-Abstract-Conference.html)
- [TimeGAN: Time-series Generative Adversarial Networks](https://proceedings.neurips.cc/paper/2019/hash/c9efe5f26cd17ba6216bbe2a7d26d490-Abstract.html)
- [GraphRNN: Generating Realistic Graphs with Deep Auto-regressive Models](https://proceedings.mlr.press/v80/you18a.html)
- [Alpha-Precision, Beta-Recall, and Authenticity](https://proceedings.mlr.press/v162/alaa22a.html)
- [NIST SP 800-226: Guidelines for Evaluating Differential Privacy Guarantees](https://doi.org/10.6028/NIST.SP.800-226)

These are candidates and measurement tools, not proof that one implementation
will be best on every DataBoom workload.

See [Neural Synthesis Research](neural-synthesis-research.md) for the implemented
Gaussian-copula, Gaussian-mixture, TensorFlow GAN, and CTGAN boundaries,
reversible transforms, provider licenses, artifact trust rules, current metrics,
local commands, and remaining production gates.
