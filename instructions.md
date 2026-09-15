# DataBoom Project Instructions

DataBoom is a production-grade data platform with four main catalog products: Table-Boom for relational data, Docu-Boom for NoSQL document data, Graph-Boom for graph data, and Masker-Boom for privacy-preserving masking/redaction workflows.

This repository is in active implementation. Keep documentation, roadmap status, and `understanding.md` aligned with significant product or architecture changes.

## Documentation Map

- [Docs Index](docs/README.md): documentation structure and separation of concerns.
- [LLM Planning and Prompt Caching](docs/engineering/prompt-caching-and-instructions.md): implemented planner boundary, prompt packs, cache telemetry, and OpenAI/Codex instruction handling.
- [DataBoom Product Family](docs/product/product-family.md): Table-Boom, Docu-Boom, Graph-Boom, Masker-Boom, and use-case naming rules.
- [High-Level Design](docs/engineering/high-level-design.md): system boundaries, plan review, engine extensibility, API flow, frontend routes, and deployment topology.
- [Low-Level Design](docs/engineering/low-level-design.md): backend modules, contracts, execution sequences, persistence, and failure boundaries.
- [Engineering Standards](docs/engineering/engineering-standards.md): reusable frontend/backend code standards and product-kind rendering rules.
- [Functional Specification](docs/product/functional-specification.md): users, workflows, product behavior, MVP scope, acceptance criteria, and out-of-scope items.
- [Product Reasoning and FAQ](docs/product/product-reasoning-faq.md): 4W1H reasoning, competitive positioning, sensitive-data use cases, and why a dedicated engine is needed.
- [Engineering Roadmap](docs/engineering/roadmap.md): five-phase status, objectives, deployment goals, and commit sequence.
- [Optimization Plan](docs/engineering/optimization-plan.md): backend optimization roadmap for speed, quality, profiling, blueprints, and observability.
- [Statistical and ML Synthesis Architecture](docs/engineering/statistical-synthesis-architecture.md): source-free and source-trained modes, profile contracts, model portfolio, model selection, and ML delivery stages.
- [Quality Evaluation and Benchmarks](docs/engineering/quality-evaluation-and-benchmarks.md): fidelity, utility, privacy, performance metrics, benchmark datasets, and acceptance gates.
- [Local Development](docs/operations/local-development.md): local setup, CLI generation, benchmark, and Docker Compose usage.
- [Frontend Development Plan](docs/engineering/frontend-development.md): phased Next.js workbench roadmap aligned with backend phases.
- [Design Research](docs/product/design-research.md): product and workflow lessons from adjacent tools.
- [Agent Operating Guide](AGENTS.md): persistent Codex guidance for this repository, including commit labels, phase discipline, and documentation rules.
- [Understanding Log](understanding.md): detailed beginner-friendly explanations for significant design, architecture, performance, reliability, and product decisions.

## Confirmed Scope Decisions

- MVP stack: Python 3.12, FastAPI, Typer, Pydantic, SQLAlchemy, psycopg, PostgreSQL, pytest, Docker, and Docker Compose.
- Phase 1 starts with the backend engine.
- Table-Boom, Docu-Boom, and Graph-Boom are active. Banking, healthcare, ecommerce, and similar domains are demo use cases, not products.
- Phase 1 through Phase 3 store generated artifacts on local disk.
- Phase 1 should target at least 100k generated records through streaming-friendly design.
- Phase 2 should harden scale toward 500k generated records.
- Phase 2 should complete NoSQL/document-style data support after the relational API and scale foundation are stable.
- Phase 3 completed graph data support, assisted planning, prompt telemetry, and plan review.
- Masker-Boom privacy, masking, redaction, tokenization, and integrity-preserving transformations are intentionally deferred until Phase 4.
- LLM-assisted planning must stay behind the replaceable planner interface with strict validation, explicit review, and deterministic fallback.
- ML synthesizers must stay behind a provider-neutral adapter interface. A model is promoted only when holdout evaluation shows that it beats simpler baselines while meeting privacy, performance, reproducibility, and operational gates.
- Product wording and reports must distinguish scenario-faithful generation from source-faithful synthesis. Source-free generation must not claim that it learned an unknown production distribution.
- PostgreSQL is the first supported relational database.
- Deployment readiness is required, not optional.

## Five-Phase Product Plan

1. Table-Boom backend foundation for relational data.
2. Table-Boom scale, API, CLI, profiling, Docu-Boom, and local artifact workflows.
3. LLM-assisted planning, Graph-Boom, and operator-facing experience.
4. Masker-Boom privacy, policy engine, security, and production hardening.
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

Every phase in the [Engineering Roadmap](docs/engineering/roadmap.md) includes a recommended commit sequence.

Update [Understanding Log](understanding.md) when a change is significant enough that future contributors should understand the reasoning, tradeoffs, or performance impact.

## Reusable Code Discipline

- Backend routes should stay thin and delegate generation, preview, persistence, and artifact work to reusable services.
- Frontend routes should compose reusable components instead of duplicating table, document, artifact, loading, and summary UI.
- Use product `kind` and response shape to render product-specific surfaces. Avoid hard-coded demo names in logic.
- Demo domains such as banking and healthcare can appear in examples, schemas, and profile labels, but they must not become separate product branches.

## Reusable Implementation Rule

Before adding a backend or frontend feature, first check whether an existing service, model, component, or helper already expresses the concept. Extend reusable code when the behavior is shared; create product-specific code only when the product kind needs a genuinely different data surface, such as relational tables, document collections, graph nodes/edges, or masking policy views.

## Immediate Next Objective

Start Phase 4 with the statistical quality Stage 0 contracts and measurement
layer, then Masker-Boom policy contracts, sensitive-field classification hints,
deterministic masking/tokenization, relationship-preserving transformations,
privacy validation, and audit output. Preserve the approved-plan and
deterministic-engine boundaries completed in Phase 3. Do not add neural model
dependencies until the statistical baseline and candidate promotion gates are
implemented.
