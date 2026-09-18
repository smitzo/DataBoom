# Agent Operating Guide

This file is persistent guidance for Codex in the DataBoom repository.

## Project Identity

DataBoom is a Python, FastAPI, Typer, PostgreSQL-first data platform. Its catalog has four main products: Table-Boom for relational data, Docu-Boom for NoSQL document data, Graph-Boom for graph data, and Masker-Boom for masking/redaction.

## Current Phase

Phase 3 is complete. Phase 4 is active: deterministic/grouped holdout splitting,
provider-neutral synthesis contracts, an empirical baseline, an optional
scikit-learn mixture baseline, an owned optional TensorFlow GAN, an optional
CTGAN provider, and an experimental candidate tournament are implemented.
Profile v2 quality-intent contracts, bounded deterministic CSV summaries, and
tournament profile lineage are implemented. Copula baselines, privacy attacks,
calibrated promotion gates, Masker-Boom policies, and worker hardening remain
active work.

Before implementation, read:

- `docs/README.md`
- `docs/product/functional-specification.md`
- `docs/engineering/roadmap.md`
- `docs/product/product-family.md`
- `docs/engineering/high-level-design.md`
- `docs/engineering/low-level-design.md`
- `docs/engineering/engineering-standards.md`
- `docs/engineering/statistical-synthesis-architecture.md`
- `docs/engineering/quality-evaluation-and-benchmarks.md`
- `docs/engineering/neural-synthesis-research.md`
- `docs/engineering/prompt-caching-and-instructions.md`
- `docs/product/product-reasoning-faq.md`
- `understanding.md`

## Working Rules

- Keep changes commit-sized and easy to review.
- Prefer backend engine work before frontend work.
- Build Masker-Boom through explicit privacy policies, integrity checks, and audit outputs; do not mix masking behavior into generation engines.
- Keep generated artifacts on local disk until durable object storage is implemented.
- Preserve deterministic generation through seed-based behavior.
- Favor streaming exports over full in-memory datasets.
- Reuse backend services and frontend components before adding new product-specific branches.
- Render product surfaces by product `kind` (`relational`, `document`, `graph`, `masking`) instead of demo product names.
- Update documentation when behavior, architecture, prompts, or phase scope changes.
- Update `understanding.md` for significant architecture, performance, reliability, product-scope, or non-obvious implementation decisions. Do not add entries for tiny mechanical changes, simple variable additions, or routine API calls.
- Do not introduce broad abstractions unless they support the documented phase roadmap.
- Distinguish scenario-faithful generation from source-faithful synthesis in
  contracts, reports, and product wording.
- Keep statistical and ML implementations behind provider-neutral synthesizer
  adapters and optional dependency groups. Do not load training libraries in the
  FastAPI web process.
- Treat source-derived model artifacts as sensitive. Reject restricted columns
  from the experimental worker, verify local model checksums before loading, and
  never accept untrusted Python model artifacts.
- Promote model candidates only through documented holdout quality, privacy,
  performance, reproducibility, and operational gates.

## Commit Labels

Use commit messages in this form:

```text
label: concise imperative summary
```

Allowed labels:

- `backend`
- `api`
- `cli`
- `frontend`
- `docs`
- `test`
- `infra`
- `cleanup`
- `optimization`
- `performance`
- `security`
- `release`

Examples:

- `backend: add schema graph models`
- `api: expose generation run status`
- `cli: add deterministic generate command`
- `frontend: build run dashboard`
- `docs: document prompt cache strategy`
- `test: cover foreign key dependency ordering`
- `infra: add docker compose postgres service`
- `cleanup: remove unused generator adapter`
- `optimization: stream csv export rows`
- `performance: benchmark 100k record generation`
- `security: add api key authentication`
- `release: prepare v0.1.0`

## Phase Discipline

Phase 1 should focus on Table-Boom relational generation:

- schema ingestion,
- schema models,
- relationship graph,
- deterministic generation,
- CSV and SQL export,
- validation reports,
- CLI entry point,
- 100k record benchmark.

Phase 2 should focus on Table-Boom scale and Docu-Boom:

- 500k record target,
- FastAPI run workflow,
- live PostgreSQL introspection,
- structural profiling,
- Docker Compose,
- local artifact management.

Phase 3 completed LLM-assisted planning and Graph-Boom:

- LLM-assisted planning,
- prompt packs,
- prompt caching metrics,
- plan review,
- optional frontend.

Phase 4 should introduce Masker-Boom:

- statistical profile v2 and quality-intent contracts,
- holdout evaluation, quality reports, and statistical baselines,
- experimental neural candidates behind the isolated ML worker boundary,
- privacy policies,
- masking and hashing,
- privacy validation,
- security hardening.

Phase 5 should finish:

- mixture and optional neural candidate tournaments,
- relational, temporal, and graph-native quality evaluation,
- model lineage, privacy attack evaluation, and worker isolation,
- production deployment,
- CI,
- observability,
- release process,
- adapter extensibility.

## Prompt and Instruction Hygiene

- Keep durable instructions in this file and stable docs.
- Keep task-specific instructions in the active user prompt.
- Avoid adding timestamps, run IDs, or temporary details to stable instruction files.
- Keep stable LLM instruction blocks and output schemas before variable metadata and user input.
- Version prompt packs and preserve cache, token, latency, validation, and fallback telemetry.

## Verification Expectations

For code changes, prefer:

- unit tests for schema parsing, dependency ordering, generation, and validation,
- integration tests for PostgreSQL behavior,
- golden-file tests for SQL and CSV output,
- performance checks for 100k and 500k record targets,
- documentation updates for changed behavior.
