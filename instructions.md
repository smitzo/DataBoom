# DataBoom Project Instructions

DataBoom is a production-grade synthetic data engine for generating realistic datasets from prompts, PostgreSQL schemas, optional database profiling, and later document and graph data specifications.

This repository is in active implementation. Keep documentation, roadmap status, and `understanding.md` aligned with significant product or architecture changes.

## Documentation Map

- [Prompt Caching and Instructions](docs/prompt-caching-and-instructions.md): prompt architecture, cache-friendly instruction layout, prompt library, and OpenAI/Codex instruction handling.
- [Functional Specification](docs/functional-specification.md): users, workflows, product behavior, MVP scope, acceptance criteria, and out-of-scope items.
- [Product Reasoning and FAQ](docs/product-reasoning-faq.md): 4W1H reasoning, competitive positioning, sensitive-data use cases, and why a dedicated engine is needed.
- [Technical Design and Roadmap](docs/technical-design-and-roadmap.md): stack, high-level design, low-level design, five-phase technical plan, deployment objectives, and commit sequence.
- [Phase 1 Usage](docs/phase1-usage.md): local setup, CLI generation, benchmark, and Docker Compose usage.
- [Frontend Development Plan](docs/frontend-development.md): phased Next.js workbench roadmap aligned with backend phases.
- [Synthetic Data Inspiration Notes](docs/synthetic-data-inspiration.md): lessons from Tonic.ai, Gretel Synthetics, and generatedata.com.
- [Agent Operating Guide](AGENTS.md): persistent Codex guidance for this repository, including commit labels, phase discipline, and documentation rules.
- [Understanding Log](understanding.md): detailed beginner-friendly explanations for significant design, architecture, performance, reliability, and product decisions.

## Confirmed Scope Decisions

- MVP stack: Python 3.12, FastAPI, Typer, Pydantic, SQLAlchemy, psycopg, PostgreSQL, pytest, Docker, and Docker Compose.
- Phase 1 starts with the backend engine.
- Phase 1 and Phase 2 store generated artifacts on local disk.
- Phase 1 should target at least 100k generated records through streaming-friendly design.
- Phase 2 should harden scale toward 500k generated records.
- Phase 2 should add NoSQL/document-style data support after the relational API and scale foundation are stable.
- Phase 3 should add graph data support for nodes, edges, properties, and graph exports.
- Privacy and field-level masking are intentionally deferred until later phases.
- LLM-assisted planning should be introduced in Phase 2 or Phase 3 behind a replaceable interface.
- PostgreSQL is the first supported relational database.
- Deployment readiness is required, not optional.

## Five-Phase Product Plan

1. Backend engine foundation.
2. Scale, API, CLI, profiling, NoSQL document data, and local artifact workflows.
3. LLM-assisted planning, graph data, and operator-facing experience.
4. Privacy, policy engine, security, and production hardening.
5. Production release, deployment automation, observability, and extensibility.

## Commit Discipline

Build this project as a clear sequence of small commits. Each commit should represent one logical improvement and use a scoped label:

- `backend: add schema graph models`
- `api: expose generation plan endpoint`
- `cli: add generate command`
- `frontend: build run status dashboard`
- `docs: split product scope documents`
- `test: cover dependency ordering`
- `infra: add docker compose postgres service`
- `cleanup: remove unused planner branch`
- `optimization: stream csv export rows`
- `performance: reduce relationship lookup memory`
- `security: add api key authentication`

Every phase in [Technical Design and Roadmap](docs/technical-design-and-roadmap.md) includes a recommended commit sequence.

Update [Understanding Log](understanding.md) when a change is significant enough that future contributors should understand the reasoning, tradeoffs, or performance impact.

## Immediate Next Objective

Continue Phase 2 planning and implementation with scale, API workflows, profiling, and NoSQL document data support while keeping commits small and reviewable.
