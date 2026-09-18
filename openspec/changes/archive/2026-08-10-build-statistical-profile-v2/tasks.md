## 1. Contracts

- [x] 1.1 Add versioned quality-intent, profile, column-summary, dependency, and artifact contracts.
- [x] 1.2 Validate profile configuration and quality-intent column references against the reviewed dataset contract.
- [x] 1.3 Extend tournament reports with optional training, holdout, and synthetic profile lineage paths.

## 2. Deterministic profiling

- [x] 2.1 Implement exact streaming source, row-count, and missingness evidence.
- [x] 2.2 Implement deterministic hash-priority sampling with bounded row memory.
- [x] 2.3 Implement numeric quantiles, histograms, skew, and tail summaries.
- [x] 2.4 Implement categorical frequency, missingness-pattern, and pairwise dependency summaries.
- [x] 2.5 Write and verify checksummed Profile v2 JSON artifacts beneath an explicit root.

## 3. Worker and tournament integration

- [x] 3.1 Add a `databoom-ml profile` command for reviewed local CSVs.
- [x] 3.2 Write training and holdout profiles once per tournament.
- [x] 3.3 Write a synthetic profile for each completed candidate without weakening existing gates.

## 4. Tests

- [x] 4.1 Add controlled mixed-type fixtures with missingness, tails, and known dependencies.
- [x] 4.2 Test contract validation, determinism, sample bounds, statistics, and malformed inputs.
- [x] 4.3 Test profile path/checksum integrity, CLI output, tournament lineage, and API import isolation.

## 5. Documentation and verification

- [x] 5.1 Update architecture, quality, roadmap, operations, package, and understanding documents.
- [x] 5.2 Run focused and full pytest, Ruff, package/import, Docker, OpenSpec strict, and diff checks.
- [x] 5.3 Mark tasks complete, archive the change, validate canonical specs, and create reviewable commits.
