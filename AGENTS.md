# Agent Operating Guide

This file is persistent guidance for Codex in the DataBoom repository.

## Project Identity

DataBoom is a Python, FastAPI, Typer, PostgreSQL-first data platform. Its catalog has four main products: Table-Boom for relational data, Docu-Boom for NoSQL document data, Graph-Boom for graph data, and Masker-Boom for masking/redaction.

## Current Phase

Phase 3 is complete: Graph-Boom, provider-neutral assisted planning, versioned prompt packs, cache telemetry, plan review, and approved-plan execution are implemented. Current work starts Phase 4 with Masker-Boom privacy policies and security hardening.

Before implementation, read:

- `instructions.md`
- `docs/README.md`
- `docs/product/functional-specification.md`
- `docs/engineering/roadmap.md`
- `docs/product/product-family.md`
- `docs/engineering/high-level-design.md`
- `docs/engineering/low-level-design.md`
- `docs/engineering/engineering-standards.md`
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

- privacy policies,
- masking and hashing,
- privacy validation,
- security hardening.

Phase 5 should finish:

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
