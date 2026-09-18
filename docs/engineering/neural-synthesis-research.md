# Classical And Neural Tabular Synthesis Research And Product Decisions

This document connects primary research to DataBoom's implemented neural
synthesis boundary. It explains what a GAN can contribute, what it cannot prove,
why DataBoom includes a classical joint baseline plus owned and provider neural
candidates, how they are evaluated, and which controls still block production
promotion.

The canonical model portfolio remains in
[Statistical and ML Synthesis Architecture](statistical-synthesis-architecture.md).
Metrics and release gates remain in
[Quality Evaluation and Benchmarks](quality-evaluation-and-benchmarks.md). This
document owns the research-to-implementation rationale.

## Executive Decision

DataBoom now has an experimental neural candidate path, but it is not a
GAN-first product.

The current order is:

1. create deterministic train, validation, and untouched holdout artifacts,
2. fit the owned independent empirical baseline,
3. fit the owned bounded Gaussian-copula joint baseline,
4. fit the optional scikit-learn Gaussian-mixture joint baseline when installed,
5. fit the owned optional TensorFlow GAN and optional CTGAN provider only when
   their dependencies and source policy are approved,
6. sample each candidate with the same row count and evaluation seed,
7. evaluate structural validity, fidelity, diversity, exact-copy exposure,
   performance, and reproducibility separately,
8. recommend the simplest candidate that passes every implemented hard gate,
9. keep the recommendation experimental until missing utility, privacy attack,
   signing, worker-isolation, and threshold-calibration evidence is complete.

A GAN is therefore one competitor. It never bypasses schema rules, privacy
policy, holdout evaluation, or human review.

## What A GAN Learns

A generative adversarial network trains two neural networks in competition:

- the generator maps random noise, and sometimes conditions, into candidate
  rows;
- the discriminator or critic tries to distinguish source rows from generated
  rows;
- training updates both networks until the generator produces samples that are
  harder for the discriminator to separate.

The original [Generative Adversarial Nets paper](https://proceedings.neurips.cc/paper/2014/hash/f033ed80deb0234979a61f95710dbe25-Abstract.html)
defines this minimax framing. That idea is powerful, but ordinary GANs were
developed around continuous tensors such as images. Tables introduce additional
problems:

- continuous columns can be non-Gaussian and multimodal;
- categorical columns are discrete and often severely imbalanced;
- null is different from zero and from an empty string;
- a row mixes several storage and semantic types;
- rare categories and small clusters are vulnerable to mode collapse;
- a discriminator loss does not say whether business constraints, privacy, or
  downstream analytics are acceptable.

## Why DataBoom Owns A Gaussian-Copula Baseline

`GaussianCopulaAdapter` is the always-available joint baseline between independent
sampling and optional ML runtimes. It retains a deterministic hash-priority row
sample, fits empirical continuous and frequency-then-lexical discrete marginals,
maps their ranks into latent normal features, regularizes the correlation matrix,
and verifies a finite Cholesky factor.

Nullable columns receive separate missingness features, so sampling can restore
empty CSV nulls while retaining measured missingness associations. The model is
data-only JSON and contains at most the configured sample bound of raw marginal
values per column. Those reviewed values remain source-derived and sensitive even
though the artifact cannot execute code.

Frequency-then-lexical ordering is deterministic, but it does not make a nominal
category ordinal. The adapter is therefore an inspectable rank-dependence
baseline, not a universal categorical model, privacy mechanism, or production
promotion claim.

## Why A Gaussian Mixture Is Another Joint Classical Candidate

Independent empirical sampling is cheap and deterministic, but it samples each
column separately and therefore cannot preserve joint structure. The optional
`SklearnGaussianMixtureAdapter` provides a stronger classical comparison before
neural complexity is considered.

The adapter converts continuous values, categorical values, and missingness into
a reversible bounded numeric representation, fits a Gaussian mixture, and stores
only the mixture parameters plus transformation metadata as JSON. Sampling is
implemented by DataBoom from those recorded parameters, so it does not need to
deserialize a scikit-learn pickle.

This is an experimental joint mechanism, not a complete controlled-population
model. One-hot categories and bounded numeric scaling can still produce smoothed
or invalid combinations, and the current evaluator does not yet measure joint
dependencies directly. Its role is to establish a cheap, inspectable candidate
that neural models must compete against.

## Why DataBoom Owns A Small TensorFlow GAN

The optional `TensorflowGanAdapter` provides an internally owned generic GAN
boundary under the permissive Apache-2.0 TensorFlow runtime. It uses the same
reversible mixed-type encoding as the Gaussian-mixture adapter, trains a bounded
generator/discriminator pair, and persists only the generator in Keras v3
format. Sampling loads that generator in safe mode without custom objects.

The model is intentionally modest. Its purpose is to prove that DataBoom can own
and replace neural architecture while preserving the same contracts, worker
isolation, lineage, checksums, transforms, and quality gates. A generic GAN does
not include CTGAN's imbalance-aware conditional training, so it is not expected
to win every mixed-table benchmark. TensorFlow determinism also remains
best-effort across devices and builds.

## Why CTGAN Remains A Neural Provider Benchmark

[CTGAN](https://proceedings.neurips.cc/paper/2019/hash/254ed7d2de3b23ab10936522dd547b78-Abstract.html)
was designed specifically for mixed tabular data. The paper's relevant ideas
are:

- mode-specific normalization for non-Gaussian continuous columns;
- a conditional vector that lets training focus on particular discrete values;
- training-by-sampling to give imbalanced categories useful exposure;
- a packed discriminator derived from
  [PacGAN](https://proceedings.neurips.cc/paper/2018/hash/288cc0ff022877bd3df94bc9360b9c5d-Abstract.html)
  to reduce mode collapse.

Those mechanisms directly address common Table-Boom workloads, so CTGAN is a
reasonable mixed-tabular provider benchmark. They do not establish that CTGAN is best for
every table. Small datasets, simple marginals, very high-cardinality identifiers,
strong temporal ordering, or multi-table conditional structure may favor a
statistical or shape-specific model.

### Current provider integration

DataBoom's `CtganAdapter` wraps the maintained standalone
[CTGAN project](https://github.com/sdv-dev/CTGAN). The optional dependency is
pinned to the reviewed [PyPI 0.12.1 release](https://pypi.org/project/ctgan/).
The adapter:

- imports pandas, NumPy, torch, and CTGAN only inside the ML worker;
- requires a reviewed column contract;
- rejects columns still marked `restricted`;
- maps discrete nulls to a reserved category;
- represents continuous missingness with a helper indicator and median
  imputation, then restores nulls after sampling;
- records hyperparameters, seeds, dependency versions, transformations, fit
  time, artifact checksum, and provider license in model lineage;
- stores the provider model as a local, checksummed Python pickle;
- verifies path containment and checksum before loading that pickle.

The standalone package currently declares BUSL-1.1 and pre-alpha status in its
package metadata. This is an engineering and product constraint, not a footnote.
DataBoom therefore keeps CTGAN optional and records the provider license in every
manifest. Commercial distribution requires a separate licensing decision. The
core splitter, contracts, empirical and Gaussian-copula baselines,
Gaussian-mixture adapter, TensorFlow adapter, evaluator, and tournament do not
depend on that package.

## Why We Do Not Implement A Generic GAN From Scratch First

A production tabular GAN requires more than two multilayer perceptrons. It also
requires reversible mixed-type transformation, conditional sampling, stable
training, missingness handling, artifact serialization, deterministic seeds,
quality evaluation, privacy diagnostics, and operational isolation.

Implementing only a generator and discriminator would create code that looks
like ML but does not create a trustworthy product. The current provider adapter
lets DataBoom validate the harder platform boundary first. If licensing or
provider maturity is unacceptable, a later OpenSpec change can replace it with
an internally owned PyTorch implementation while preserving the same dataset,
adapter, lineage, sample, and report contracts.

Research on training stability still informs that future implementation.
[WGAN-GP](https://proceedings.neurips.cc/paper/2017/hash/892c3b1c6dccd52936e27cbd0ff683d6-Abstract.html)
replaces problematic critic weight clipping with a gradient penalty. It is
useful background for stable adversarial training, but it is not by itself a
mixed-tabular solution.

## Missing Values And Type Restoration

The maintained standalone CTGAN documentation expects preprocessed continuous
and discrete columns. DataBoom owns the reversible boundary because the output
must return to the reviewed CSV contract.

For a discrete nullable column:

1. choose a reserved null token that does not collide with observed categories,
2. train the provider on that category,
3. replace the reserved token with null after sampling.

For a continuous nullable column:

1. create a discrete missingness indicator,
2. fill missing numeric values with the training median,
3. include the indicator in GAN training,
4. set sampled values back to null when the sampled indicator is active,
5. remove the helper column before export.

This preserves basic null rates and permits dependency learning between
missingness and other fields. The first evaluator does not yet fully measure
conditional missingness, so that remains a documented Q1 gap.

## Why GAN Loss Is Not A Product Quality Score

Generator and discriminator losses describe the training game. They do not
answer whether:

- CSV columns and types match the contract,
- a rare category disappeared,
- numeric tails are wrong,
- generated rows duplicate training subjects,
- a downstream classifier retains utility,
- training meets latency and memory budgets,
- repeated seeds produce reproducible artifacts,
- a formal privacy mechanism exists.

DataBoom evaluates model output instead of promoting on training loss. The first
implemented report includes:

| Dimension | Implemented evidence | Important limitation |
| --- | --- | --- |
| Structural | Exact column order, row count, numeric parsing, required null checks. | Cross-column business constraints are not yet connected. |
| Numeric fidelity | Kolmogorov-Smirnov statistic and mean error normalized by holdout spread. | Quantiles, tails, covariance, and mixed dependencies remain. |
| Categorical fidelity | Total-variation distance including null as a category. | Rare-category confidence intervals remain. |
| Diversity | Whole-row synthetic uniqueness. | Cluster coverage and richer mode-collapse metrics remain. |
| Privacy diagnostic | Exact synthetic-to-training row match rate. | Near-neighbor, membership, and attribute inference remain. |
| Performance | Fit and sample wall time. | Peak CPU/GPU memory and cost telemetry remain. |
| Reproducibility | Repeat sample checksum for the same model and seed. | GPU/provider nondeterminism may require tolerance-based evidence. |

The initial thresholds are explicitly named `experimental-tabular-v1`. They are
test and development defaults, not a universal production policy. They must be
calibrated on controlled fixtures and public benchmarks before release claims.

## Privacy: Synthetic Does Not Mean Anonymous

A GAN can memorize rare or unique source rows. High local fidelity may increase
disclosure risk. Exact-match detection is therefore a minimum gate, not a
privacy proof.

[Alpha-Precision, Beta-Recall, and Authenticity](https://proceedings.mlr.press/v162/alaa22a.html)
separates fidelity, diversity, and generalization/copying evidence. DataBoom's
future evaluator should add those sample-level metrics rather than rely only on
column distances.

Formal privacy requires an actual privacy mechanism and accounting. Research
such as [PATE-GAN](https://openreview.net/forum?id=S1zk9iRqF7) explores a
differentially private GAN design. DataBoom does not implement or claim that
mechanism today. [NIST SP 800-226](https://csrc.nist.gov/pubs/sp/800/226/final)
is the operations reference for evaluating differential privacy guarantees and
their implementation hazards.

Until the privacy program is complete, model artifacts and reports are treated
as source-derived sensitive assets. A report uses `empirically audited` and
`experimental`, never `anonymous` or `privacy-safe`.

## Why The Worker Boundary Matters

Training libraries are deliberately absent from the normal FastAPI import graph.
The base service can start, serve health checks, plan deterministic runs, and
generate ordinary artifacts when every optional training extra is absent.

The dedicated `databoom-ml` process owns:

- source CSV reads,
- split artifacts,
- provider-specific in-memory matrices or dataframes,
- model fitting,
- executable model files,
- candidate samples,
- evaluation and tournament reports.

The current worker is a local CLI isolation boundary, not a hardened sandbox.
Production still requires a separate image/process identity, resource limits,
queue ownership, cancellation, signed manifests, durable model storage, and
restricted network/filesystem access.

## Model Artifact Security

The empirical, Gaussian-copula, and Gaussian-mixture artifacts are data-only JSON.
The copula artifact still contains bounded raw marginal values, so it needs the
same protected source-derived storage as the empirical artifact. The TensorFlow
candidate stores a Keras v3 generator and loads it in safe mode without custom
objects. CTGAN is persisted with Python pickle because the provider model is a
Python object graph. Pickle can execute code during loading. SHA-256 proves that
bytes match a recorded manifest; it does not prove those bytes are benign if an
attacker can replace both the model and manifest.

Current rule:

- load only artifacts created locally inside the declared experiment root,
- reject absolute paths and directory traversal,
- verify the model checksum before deserialization,
- never expose a general upload/load endpoint,
- keep `trusted_local_only=true` in the manifest.

Production follow-up:

- sign manifests or store checksums in a separately protected registry,
- isolate deserialization in a low-privilege worker,
- prefer data-only formats when an adapter can reconstruct from tensors and JSON,
- scan dependency and image provenance,
- define deletion and retention policy for source-derived models.

## Current Command Flow

Install the base development environment:

```bash
.venv/bin/python -m pip install -e '.[dev]'
```

Inspect available candidates without importing a provider runtime:

```bash
.venv/bin/python -m databoom.synthesis.cli capabilities
```

Create group-preserving split artifacts:

```bash
.venv/bin/python -m databoom.synthesis.cli split source.csv \
  --output-dir artifacts/ml/split \
  --group-column customer_id \
  --seed split-1
```

Create a reviewed dataset contract. Sensitivity is restrictive by default, so
every training-eligible column must be explicitly classified:

```json
{
  "contract_version": "1",
  "name": "customer_quality_fixture",
  "columns": [
    {
      "name": "age",
      "kind": "continuous",
      "nullable": false,
      "sensitivity": "non_sensitive"
    },
    {
      "name": "segment",
      "kind": "discrete",
      "nullable": true,
      "sensitivity": "non_sensitive"
    }
  ]
}
```

Create standalone, checksummed Profile v2 evidence before training:

```bash
.venv/bin/python -m databoom.synthesis.cli profile source.csv \
  dataset-contract.json \
  --output-dir artifacts/ml/source-profile \
  --sample-row-limit 10000 \
  --seed profile-1
```

The profiler keeps exact source fingerprints, row counts, and null counts while
deriving heavier distribution and dependency summaries from a deterministic,
bounded hash-priority sample. Tournament runs create equivalent training,
holdout, and per-candidate synthetic profile artifacts automatically.

Run the owned baseline:

```bash
.venv/bin/python -m databoom.synthesis.cli tournament \
  artifacts/ml/split/split-manifest.json \
  dataset-contract.json \
  --experiment-root artifacts/ml/empirical-experiment \
  --candidate empirical-independent \
  --sample-rows 10000
```

Install the optional classical joint baseline and compare it with the empirical
candidate:

```bash
.venv/bin/python -m pip install -e '.[dev,ml-sklearn]'
.venv/bin/python -m databoom.synthesis.cli tournament \
  artifacts/ml/split/split-manifest.json \
  dataset-contract.json \
  --experiment-root artifacts/ml/gmm-experiment \
  --candidate empirical-independent \
  --candidate sklearn-gaussian-mixture \
  --gmm-components 5 \
  --sample-rows 10000
```

Install the owned optional TensorFlow GAN when the larger worker dependency is
appropriate:

```bash
.venv/bin/python -m pip install -e '.[dev,neural-tensorflow]'
.venv/bin/python -m databoom.synthesis.cli tournament \
  artifacts/ml/split/split-manifest.json \
  dataset-contract.json \
  --experiment-root artifacts/ml/tensorflow-experiment \
  --candidate empirical-independent \
  --candidate tensorflow-gan \
  --tensorflow-epochs 100 \
  --sample-rows 10000
```

Install and explicitly request the optional CTGAN provider only after license
and source-policy review:

```bash
.venv/bin/python -m pip install torch \
  --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -e '.[dev,neural-ctgan]'
.venv/bin/python -m databoom.synthesis.cli tournament \
  artifacts/ml/split/split-manifest.json \
  dataset-contract.json \
  --experiment-root artifacts/ml/ctgan-experiment \
  --candidate empirical-independent \
  --candidate ctgan \
  --ctgan-epochs 300 \
  --sample-rows 10000
```

The CPU-wheel step is explicit because the default Linux PyPI PyTorch package
can resolve a large CUDA dependency stack even though this adapter declares no
GPU requirement. GPU workers must instead pin and validate their own CUDA,
driver, torch, and image versions.

## Candidate Portfolio Beyond The Current Adapters

The empirical, Gaussian-copula, Gaussian-mixture, TensorFlow GAN, and CTGAN
adapters establish a comparison boundary; they are not the endpoint.

| Candidate | Research basis | What it may improve | Why it is not automatic |
| --- | --- | --- | --- |
| TVAE | CTGAN paper includes a variational autoencoder baseline. | More stable likelihood-style training on some tables. | Can smooth rare modes and still copy or leak training structure. |
| TabDDPM | [TabDDPM](https://proceedings.mlr.press/v202/kotelnikov23a.html) | Heterogeneous tabular fidelity through diffusion. | Sampling cost, dependency weight, and workload-specific results must be measured. |
| TabSyn | [TabSyn](https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9750610639c3e7a849cff746bf60dbd-Abstract-Conference.html) | Latent diffusion for mixed-type tables. | More moving parts, compute, and artifact governance. |
| TimeGAN | [TimeGAN](https://proceedings.neurips.cc/paper/2019/hash/c9efe5f26cd17ba6216bbe2a7d26d490-Abstract.html) | Sequence dynamics and temporal relationships. | A single-table row tournament cannot evaluate sequence fidelity. |
| GraphRNN | [GraphRNN](https://proceedings.mlr.press/v80/you18a.html) | Native graph topology generation. | Graph-Boom requires degree, community, path, and endpoint-specific gates. |

Each future adapter must use the same rule: include simpler baselines, reserve
holdout data, use shape-native metrics, audit privacy, record cost, and promote
only through evidence.

## Next Research And Engineering Gates

1. Add alpha-precision, beta-recall, authenticity, nearest-neighbor, and
   train-versus-holdout distance diagnostics.
2. Add downstream train-synthetic/test-real utility with identical preprocessing
   and tuning budgets.
3. Add peak memory, device, package-image, failure, retry, and cancellation
   telemetry.
4. Calibrate thresholds with controlled fixtures, UCI Bank Marketing, and UCI
   Covertype across repeated seeds.
5. Resolve provider licensing and decide whether to ship CTGAN, isolate it as an
   external provider, or build an internally owned implementation.
6. Move fitting and deserialization into a hardened worker before any public API
   orchestrates source-trained runs.

## Primary References

- [Generative Adversarial Nets, NeurIPS 2014](https://proceedings.neurips.cc/paper/2014/hash/f033ed80deb0234979a61f95710dbe25-Abstract.html)
- [Improved Training of Wasserstein GANs, NeurIPS 2017](https://proceedings.neurips.cc/paper/2017/hash/892c3b1c6dccd52936e27cbd0ff683d6-Abstract.html)
- [PacGAN, NeurIPS 2018](https://proceedings.neurips.cc/paper/2018/hash/288cc0ff022877bd3df94bc9360b9c5d-Abstract.html)
- [CTGAN, NeurIPS 2019](https://proceedings.neurips.cc/paper/2019/hash/254ed7d2de3b23ab10936522dd547b78-Abstract.html)
- [PATE-GAN, ICLR 2019](https://openreview.net/forum?id=S1zk9iRqF7)
- [Alpha-Precision, Beta-Recall, and Authenticity, ICML 2022](https://proceedings.mlr.press/v162/alaa22a.html)
- [TabDDPM, ICML 2023](https://proceedings.mlr.press/v202/kotelnikov23a.html)
- [TabSyn, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9750610639c3e7a849cff746bf60dbd-Abstract-Conference.html)
- [NIST SP 800-226, Guidelines for Evaluating Differential Privacy Guarantees](https://csrc.nist.gov/pubs/sp/800/226/final)
