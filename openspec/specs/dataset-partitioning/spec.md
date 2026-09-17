# dataset-partitioning Specification

## Purpose
Define reproducible train, validation, and holdout partitioning with group
isolation, checksummed evidence, and bounded-memory CSV processing.

## Requirements
### Requirement: Deterministic partitioning
The system MUST partition a supported local CSV into disjoint training,
validation, and holdout artifacts using a versioned algorithm, declared ratios,
and seed.

#### Scenario: Same input and seed
- **WHEN** the same CSV, ratios, grouping configuration, algorithm version, and seed are partitioned twice
- **THEN** the system produces byte-equivalent partition contents and matching fingerprints

#### Scenario: Invalid ratio configuration
- **WHEN** ratios are non-positive or do not sum to one within the documented tolerance
- **THEN** the system rejects the request before writing a completed split manifest

### Requirement: Subject-preserving split
When group columns are configured, the system MUST assign every row sharing the
same normalized group key to exactly one partition.

#### Scenario: Repeated subject rows
- **WHEN** multiple source rows share the configured subject identifier
- **THEN** none of those rows appears in more than one of training, validation, or holdout

#### Scenario: Missing group column
- **WHEN** a requested group column is absent from the CSV header
- **THEN** the system rejects the split with the missing column identified

### Requirement: Split evidence
The system MUST write a machine-readable manifest containing the source
fingerprint, split algorithm and seed, ratios, group columns, per-partition row
counts, paths, and SHA-256 fingerprints.

#### Scenario: Successful split
- **WHEN** all three partitions contain rows and pass overlap validation
- **THEN** the completed manifest contains enough evidence to reproduce and verify the split

### Requirement: Bounded row memory
The partition writer MUST stream CSV rows and MUST NOT materialize the complete
source table as Python row objects.

#### Scenario: Large CSV
- **WHEN** the source contains more rows than the configured write buffer
- **THEN** partition output is produced incrementally with memory independent of total row count apart from configured group diagnostics
