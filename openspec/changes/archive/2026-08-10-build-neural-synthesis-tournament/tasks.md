## 1. Contracts and packaging

- [x] 1.1 Add versioned synthesis, split, lineage, metric, policy, and decision contracts.
- [x] 1.2 Add provider-neutral adapter protocol, capability registry, and unavailable-provider errors.
- [x] 1.3 Add optional scikit-learn, TensorFlow CPU, and CTGAN dependency groups plus the isolated ML worker entry point.

## 2. Dataset partitioning

- [x] 2.1 Implement deterministic streaming row and group-preserving CSV splitting.
- [x] 2.2 Write split manifests with source, partition, algorithm, row-count, and checksum evidence.
- [x] 2.3 Test determinism, group isolation, invalid ratios, missing columns, and empty partitions.

## 3. Synthesizer adapters

- [x] 3.1 Implement the mixed-type independent empirical baseline with JSON model artifacts.
- [x] 3.2 Implement the optional lazy CTGAN adapter with reversible null preprocessing.
- [x] 3.3 Verify model paths and checksums before loading executable provider artifacts.
- [x] 3.4 Test baseline determinism, optional dependency failure, API import isolation, and artifact tampering.
- [x] 3.5 Implement an optional scikit-learn Gaussian-mixture adapter with a data-only JSON artifact.
- [x] 3.6 Implement an owned optional TensorFlow GAN adapter with Keras generator artifacts.
- [x] 3.7 Test scikit-learn and TensorFlow capability discovery, transforms, sampling, and dependency isolation.

## 4. Evaluation and tournament

- [x] 4.1 Implement structural, numeric, categorical, diversity, exact-copy, and performance metrics.
- [x] 4.2 Implement explicit hard gates and experimental evidence-completeness decisions.
- [x] 4.3 Implement candidate orchestration with fixed sample counts and evaluation seeds.
- [x] 4.4 Add worker CLI commands for split, capability inspection, and local tournament execution.
- [x] 4.5 Test hard-gate precedence, candidate failure isolation, and machine-readable artifacts.

## 5. Documentation and repository guidance

- [x] 5.1 Add a primary-research-backed GAN and neural synthesis engineering guide.
- [x] 5.2 Update canonical architecture, quality, roadmap, operations, package, and documentation indexes.
- [x] 5.3 Record the worker, license, pickle, evaluation, and non-promotion decisions in `understanding.md`.
- [x] 5.4 Remove superseded `instructions.md` references and delete the file.

## 6. Verification and archive

- [x] 6.1 Run focused synthesis tests, full pytest, Ruff, package import, and FastAPI startup checks.
- [x] 6.2 Validate the OpenSpec change strictly and run `git diff --check`.
- [x] 6.3 Mark completed tasks, archive the OpenSpec change, and validate the archived specs.
