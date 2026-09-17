# candidate-tournament Specification

## Purpose
Define comparable, evidence-producing execution and experimental promotion
boundaries for source-trained synthesizer candidates.

## Requirements
### Requirement: Comparable candidate execution
The tournament MUST fit candidates on the training partition and sample the same
row count with the same evaluation seed before comparing them against untouched
holdout data.

#### Scenario: Multiple eligible candidates
- **WHEN** empirical, scikit-learn, TensorFlow GAN, or CTGAN adapters are eligible
- **THEN** each receives the same split manifest, sample count, and evaluation seed and retains separate fit and sample timings

#### Scenario: Candidate failure
- **WHEN** one adapter fails during fit or sample
- **THEN** its failure is recorded without discarding completed evidence from other candidates

### Requirement: Multidimensional quality report
The evaluator MUST report structural validity, numeric distribution distance,
categorical distribution distance, diversity, exact training-row exposure,
performance, reproducibility, warnings, and evidence completeness separately.

#### Scenario: Average score hides a hard failure
- **WHEN** a candidate has strong fidelity but exceeds the configured exact-match limit
- **THEN** the privacy hard gate fails regardless of its aggregate fidelity

### Requirement: No automatic production promotion
The first tournament MUST label decisions as experimental and MUST NOT describe
output as anonymous, privacy-safe, or production-approved.

#### Scenario: All implemented gates pass
- **WHEN** a candidate passes every currently implemented gate
- **THEN** the report may recommend it for further controlled evaluation but records missing production evidence and keeps release approval false

### Requirement: Human-readable and machine-readable evidence
The tournament MUST write a JSON experiment manifest and quality report that can
be inspected without importing a model provider.

#### Scenario: Completed tournament
- **WHEN** at least one candidate completes evaluation
- **THEN** an operator can inspect candidate metrics, gate outcomes, lineage paths, and recommendation from JSON artifacts alone
