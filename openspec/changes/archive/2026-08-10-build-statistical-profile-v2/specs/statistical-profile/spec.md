## ADDED Requirements

### Requirement: Versioned quality intent and profile contracts
The system MUST represent a reviewed dataset's quality intent and statistical
Profile v2 evidence through immutable, provider-neutral, versioned contracts.

#### Scenario: Quality intent references an unknown column
- **WHEN** an intent weights or protects a column absent from its dataset contract
- **THEN** contract validation rejects the intent before profiling starts

#### Scenario: Profile artifact is inspected without ML extras
- **WHEN** a Profile v2 JSON artifact is loaded in the base installation
- **THEN** all evidence is available without importing an optional training dependency

### Requirement: Deterministic bounded-memory profiling
The CSV profiler MUST retain at most the configured sample-row bound while
computing an exact source fingerprint, total row count, and per-column null counts.

#### Scenario: Source exceeds the sample bound
- **WHEN** a CSV contains more rows than the configured profile sample limit
- **THEN** the profiler uses a versioned hash-priority sample and records the source and sampled row counts separately

#### Scenario: Same source and configuration
- **WHEN** the same source, dataset contract, intent, sample limit, and seed are profiled twice
- **THEN** their profile identifiers and statistical evidence match apart from creation time and output location

### Requirement: Typed univariate summaries
Profile v2 MUST report exact missingness and sampled numeric or categorical
distribution evidence appropriate to each reviewed column kind.

#### Scenario: Continuous column has finite observations
- **WHEN** a continuous column contains finite non-null values
- **THEN** its profile reports min, max, mean, standard deviation, skew, configured quantiles, histogram counts, and lower and upper tail rates

#### Scenario: Discrete column exceeds top-value limit
- **WHEN** a discrete column has more sampled categories than the configured limit
- **THEN** its profile reports bounded top values, other count, and top-value coverage without retaining an unbounded full-table category map

### Requirement: Missingness and dependency summaries
Profile v2 MUST report bounded missingness patterns and supported pairwise
dependency statistics with sample counts and explicit metric names.

#### Scenario: Pair of continuous columns varies
- **WHEN** two continuous columns have at least two complete sampled rows and nonzero variance
- **THEN** their dependency summary reports Pearson correlation and its contributing row count

#### Scenario: Dependency is undefined
- **WHEN** a pair lacks enough complete observations or variance
- **THEN** the profiler omits a fabricated value and records an actionable warning

### Requirement: Profile artifact integrity
Completed profile evidence MUST be written beneath an explicit artifact root with
a stable identifier, relative path, row counts, and SHA-256 checksum.

#### Scenario: Profile bytes are changed
- **WHEN** a consumer verifies a profile artifact whose bytes differ from its manifest checksum
- **THEN** verification fails before the profile is used as tournament evidence

#### Scenario: Profile path escapes its root
- **WHEN** a profile manifest resolves outside the declared artifact root
- **THEN** verification rejects the artifact before reading it
