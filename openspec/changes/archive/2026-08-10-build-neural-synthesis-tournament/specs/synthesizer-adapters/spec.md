## ADDED Requirements

### Requirement: Provider-neutral adapter capability contract
Every synthesizer adapter MUST declare its name, implementation version, data
shapes, determinism level, conditional support, CPU/GPU requirements, complexity
tier, and dependency availability through a common interface.

#### Scenario: Adapter discovery without ML extras
- **WHEN** the base DataBoom environment discovers synthesizer capabilities without optional ML packages installed
- **THEN** discovery succeeds, marks unavailable providers explicitly, and does not import a training library

### Requirement: Always-available empirical baseline
The system MUST provide an owned CPU empirical adapter that can fit and sample a
mixed-type CSV deterministically without optional neural dependencies.

#### Scenario: Baseline fit and sample
- **WHEN** a valid training partition, column contract, and seed are provided
- **THEN** the empirical adapter writes a checksummed model artifact and a sample with the original column order

### Requirement: Optional CTGAN provider
The system MUST expose CTGAN only as an optional, lazily imported provider and
MUST preserve the core application when that provider is absent or fails.

#### Scenario: Optional dependency absent
- **WHEN** CTGAN is requested in a base installation
- **THEN** the worker returns an actionable unavailable-adapter error while deterministic and empirical paths remain operational

#### Scenario: Nullable mixed table
- **WHEN** CTGAN fits a valid table containing discrete and continuous nulls
- **THEN** the adapter records its reversible null transformation and sampled output restores the original columns and null representation

### Requirement: Optional scikit-learn joint baseline
The system MUST provide a lazily imported scikit-learn candidate that models
joint structure, uses a reversible mixed-type transformation, and writes a
data-only model artifact.

#### Scenario: Classical ML extra is installed
- **WHEN** a reviewed mixed-type training partition is fitted with the scikit-learn adapter
- **THEN** the adapter records Gaussian-mixture parameters and preprocessing metadata in checksummed JSON and samples the original column contract deterministically

#### Scenario: Classical ML extra is absent
- **WHEN** the scikit-learn adapter is discovered without its optional dependency
- **THEN** capability inspection reports it unavailable without affecting FastAPI or the empirical baseline

### Requirement: Optional owned TensorFlow GAN
The system MUST provide a lazily imported TensorFlow GAN implemented inside
DataBoom and MUST store only its generator and reversible transformation for
sampling.

#### Scenario: TensorFlow GAN training
- **WHEN** the TensorFlow extra is installed and an eligible mixed-type partition is fitted
- **THEN** the worker trains the bounded GAN, stores a checksummed Keras generator, records training settings and transforms, and restores sampled CSV columns

#### Scenario: TensorFlow extra is absent
- **WHEN** the TensorFlow GAN is discovered in the base installation
- **THEN** it is reported unavailable and TensorFlow is not imported by capability discovery or FastAPI startup

### Requirement: Model lineage and local artifact integrity
Every fitted model MUST have a manifest containing adapter and dependency
versions, input fingerprint, feature contract, hyperparameters, training seed,
fit duration, artifact path, and artifact checksum.

#### Scenario: Corrupted model artifact
- **WHEN** the stored model bytes no longer match the manifest checksum
- **THEN** the worker refuses to load or sample the model

#### Scenario: Model path escape
- **WHEN** a model manifest resolves outside its declared experiment root
- **THEN** the worker rejects the artifact before deserialization

### Requirement: Training-process isolation
FastAPI startup and normal generation MUST NOT import pandas, NumPy,
scikit-learn, TensorFlow, torch, CTGAN, or another training implementation.

#### Scenario: API import in base environment
- **WHEN** the FastAPI app is imported with no ML extra installed
- **THEN** application creation and health routes remain available
