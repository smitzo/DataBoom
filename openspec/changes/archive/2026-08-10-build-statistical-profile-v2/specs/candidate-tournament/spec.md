## ADDED Requirements

### Requirement: Reusable profile lineage
The tournament MUST write training and holdout Profile v2 artifacts once per
experiment and a synthetic Profile v2 artifact for each completed candidate.

#### Scenario: Candidate completes evaluation
- **WHEN** a candidate fits, samples, and passes artifact verification
- **THEN** its result references the shared source profiles and its own checksummed synthetic profile alongside direct metric evidence

#### Scenario: Candidate profile generation fails
- **WHEN** synthetic profile generation or verification fails for one candidate
- **THEN** that candidate is recorded as failed without discarding completed evidence from other candidates

### Requirement: Profile evidence does not imply promotion
Profile v2 evidence MUST remain a separate experimental input until acceptance
thresholds are calibrated and privacy and utility gates are complete.

#### Scenario: Source and synthetic profiles appear similar
- **WHEN** current univariate and dependency summaries are close
- **THEN** the report still keeps release approval false and retains its missing production evidence
