# DataBoom Understanding Log

This file explains important project decisions: what changed, why it changed, and how the decision improves the project. Keep it beginner-friendly, but detailed enough that a new engineer can understand the professional reasoning behind significant architecture, product, performance, and reliability choices.

Not every commit needs an entry. Add an entry when the change is significant enough that a future contributor should understand the reasoning or tradeoff.

## How To Update This File

For significant changes, add a new entry using this format:

```md
## Decision: short title

### Question

- What question or tradeoff did this change answer?

### Answer

- Short direct answer.

### Why This Matters

- Explain the product, architecture, performance, reliability, or maintainability impact.

### Details

- Explain the deeper reasoning in beginner-friendly but professional language.

### Follow-Up Notes

- Mention anything intentionally deferred or any future work this decision unlocks.
```

## Commit: docs: split product scope documents

### What Changed

- Replaced the original one-paragraph `instructions.md` with a project entry point.
- Added `docs/functional-specification.md` for product behavior and workflows.
- Added `docs/technical-design-and-roadmap.md` for architecture, stack, diagrams, phases, and commit sequencing.
- Added `docs/prompt-caching-and-instructions.md` for OpenAI prompt caching and Codex instruction hygiene.
- Added `AGENTS.md` so Codex has persistent repository guidance.

### Why It Changed

The project was too important to leave as a single rough paragraph. DataBoom needs to become a production-grade synthetic data engine, so the planning documents need separation of concerns. Product behavior, technical design, prompt strategy, and agent rules all change at different speeds and are read by different audiences.

### Why This Approach

Separating the documents prevents one giant file from becoming confusing. A product reviewer can read the functional spec. An engineer can read the technical roadmap. An agent can read `AGENTS.md`. Prompt-related decisions can live in their own file so LLM behavior is not mixed into backend implementation details.

This is better than one long instruction file because it reduces accidental edits, makes reviews easier, and lets each file stay focused.

### Performance, Reliability, or Maintainability Impact

This change does not improve runtime performance because no application code exists yet. It improves maintainability by giving future commits a clear contract. It improves reliability indirectly because future implementation work must follow documented objectives instead of improvising.

### Beginner Explanation

Think of the project like a building. Before writing code, we created separate blueprints: what the building is for, how it should be constructed, how workers should coordinate, and what rules they must follow. This makes later construction faster and less chaotic.

### Follow-Up Notes

- Implementation has not started yet.
- Phase 1 should begin with the backend engine.
- Future significant decisions should update this file.

## Commit: docs: add product reasoning and backend implementation discipline

### What Changed

- Added `docs/product-reasoning-faq.md` to answer strategic questions using 4W1H reasoning.
- Added reasoning for why DataBoom is more than Faker.
- Added reasoning for why ChatGPT should not directly generate one million records.
- Added reasoning for how a streaming engine can eventually handle one million records.
- Added a careful comparison against Tonic.ai without claiming false universal superiority.
- Added sensitive-domain positioning for fintech, medical, insurance, and customer-sensitive workflows.
- Added this `understanding.md` file as a permanent explanation log.
- Updated `AGENTS.md` so significant future decisions update this file.

### Why It Changed

The project needs clear answers to hard questions before implementation begins. People will naturally ask why this engine should exist, why an LLM alone is not enough, why we cannot just use Faker, and why we would build an internal system when commercial tools exist. Capturing those answers early keeps the team aligned.

The project also needs a durable explanation trail. Code tells us what changed, but not always why. `understanding.md` preserves the reasoning behind significant decisions so future contributors can learn quickly without turning the file into a noisy changelog.

### Why This Approach

The FAQ is in `docs/` because it is product and architecture reasoning, not agent instruction. `understanding.md` is at the repository root because it should be visible when decisions are important enough to explain.

The comparison with Faker is framed carefully: Faker is useful, but incomplete. DataBoom should use Faker for fake values while adding schema parsing, relationship solving, streaming, validation, and run management around it.

The comparison with Tonic.ai is also framed carefully. Tonic.ai is a mature commercial platform. DataBoom's argument is not "Tonic is bad"; it is "we need an owned, inspectable, local-first, PostgreSQL-focused engine that we can evolve commit by commit."

The ChatGPT reasoning separates planning from execution. LLMs are strong at interpreting intent and producing plans. They are not the right execution layer for directly emitting huge relational datasets with guaranteed constraints.

### Performance, Reliability, or Maintainability Impact

The reasoning pushes the implementation toward a streaming pipeline. That matters for performance because 100k, 500k, and eventually 1M records cannot be treated as one giant in-memory object.

The documentation also improves reliability. It says schema safety wins over prompt requests, validation is required, and privacy claims should not be made before privacy features exist.

Maintainability improves because significant decisions now explain themselves. A beginner can read this file and understand why important choices were made instead of reverse-engineering intent from code.

### Beginner Explanation

Faker is like a box of fake names and addresses. ChatGPT is like a smart planner that can describe what data should look like. DataBoom needs to be the factory: it reads the database blueprint, decides which tables come first, creates rows in the right order, writes files without running out of memory, and checks that everything fits.

For one million records, the factory cannot keep every item in one huge pile. It needs a conveyor belt. That is why the roadmap emphasizes chunking, streaming, manifests, and validation.

### Follow-Up Notes

- Phase 1 still starts with backend engine foundations.
- Privacy is still deferred until Phase 4, but sensitive use cases remain part of the long-term product strategy.
- A formal 1M-record benchmark should come after the 100k and 500k milestones are stable.

## Decision: keep understanding.md for significant decisions

### Question

Should `understanding.md` explain every commit, or only decisions that are important enough to teach future contributors?

### Answer

Only significant decisions should be explained here. Routine edits, simple variables, basic API calls, and tiny mechanical fixes should stay in the git diff and commit message.

### Why This Matters

If every small change gets a long explanation, this file becomes noisy and people stop reading it. The goal is not to duplicate git history. The goal is to preserve reasoning that is hard to recover later: architecture choices, performance strategy, reliability tradeoffs, product scope decisions, and non-obvious implementation patterns.

### Details

Use `understanding.md` when a change answers a meaningful question, such as:

- Why are we streaming output instead of building one giant list?
- Why is schema safety more important than prompt freedom?
- Why are we using local disk before object storage?
- Why are we using Redis in Compose but not Celery yet?
- Why did we choose one data structure or algorithm over another?

Do not use it for changes like:

- adding one obvious field,
- renaming a local variable,
- adding a straightforward endpoint after the pattern already exists,
- fixing a typo,
- moving an import,
- adjusting formatting.

### Follow-Up Notes

- Entries can use Q&A format when that makes the reasoning easier to scan.
- Commit messages should still stay clear and scoped.
- Important performance and architecture commits should almost always update this file.

## Decision: add Docker, Postgres, and Redis without Celery or Kafka yet

### Question

Should Phase 1 infrastructure include only the application and PostgreSQL, or should it also include Redis, Celery, Kafka, and other future runtime systems?

### Answer

Phase 1 should include Docker, PostgreSQL, and Redis. It should not include Celery or Kafka until the codebase has a real async worker, queue, event-streaming, or distributed orchestration requirement.

### Why This Matters

PostgreSQL is required because DataBoom is PostgreSQL-first. Redis is useful to have early because it is lightweight and will likely support future run state, locks, queues, caching, or progress tracking. Celery and Kafka are heavier architectural commitments. Adding them before there is a concrete workflow would increase operational complexity without improving the Phase 1 backend engine.

### Details

The Compose file should make local infrastructure easy to start while keeping the application image usable for CLI commands and future API work. The app service is therefore a tool/profile service for now instead of a fake long-running worker. This avoids pretending that Phase 1 already has an API server or background job system.

The important design principle is "prepare the runway, but do not build unused machinery." Redis prepares for future orchestration. Celery or Kafka should wait until there is a specific Phase 2 or Phase 3 need, such as long-running generation jobs, progress events, retries, or distributed workers.

### Follow-Up Notes

- When API run management arrives, decide whether Redis alone is enough or whether Celery is needed.
- Kafka should only be considered if DataBoom needs durable event streams or integration with external event-driven systems.
- The Dockerfile should remain simple until production deployment hardening in Phase 5.

## Decision: normalize schemas before parsing, planning, or generation

### Question

Why does DataBoom need explicit schema model contracts instead of passing raw SQL parser output or dictionaries directly into the generator?

### Answer

The engine needs a stable internal schema representation so every later component speaks the same language. Parsers can change, API payloads can change, and future database adapters can change, but planners, relationship solvers, generators, validators, and exporters should all depend on one normalized contract.

### Why This Matters

Synthetic data generation fails quickly when schema details are inconsistent. If one part of the code calls a field `foreign_keys`, another calls it `fks`, and a third leaves it as raw SQL text, bugs become hard to trace. A normalized model catches invalid or incomplete schema data early, before generation starts producing bad output.

### Details

The schema model validates important invariants:

- tables must have columns,
- column names must be unique within a table,
- primary keys and unique constraints must reference real columns,
- foreign keys must reference real local columns,
- foreign-key local and remote column counts must match,
- database schemas must not contain duplicate qualified table names.

These checks make later code simpler. The generator should not repeatedly ask, "does this foreign key make sense?" It should receive a schema that has already passed basic structural validation.

### Follow-Up Notes

- The DDL parser should produce these models instead of inventing a separate parser-specific shape.
- Relationship graph code should use `DatabaseSchema` and `TableSchema` directly.
- Later adapters for live PostgreSQL introspection, MySQL, SQLite, or other systems can map into the same contracts.

## Decision: use sqlglot for Phase 1 DDL ingestion

### Question

Should DataBoom parse PostgreSQL DDL with a SQL parser dependency or with custom string manipulation?

### Answer

Use `sqlglot` for Phase 1 DDL parsing. It gives us a structured AST for common `CREATE TABLE` statements, which is safer than splitting strings by commas, parentheses, and keywords.

### Why This Matters

DDL looks simple until constraints, defaults, nested type parameters, quoted identifiers, and table-level foreign keys appear. A custom parser can accidentally split `decimal(10, 2)` or `UNIQUE (account_id, email)` incorrectly. That kind of bug would corrupt the schema model before generation even starts.

### Details

The ingestion layer should convert SQL parser output into DataBoom's normalized `DatabaseSchema`. The rest of the engine should not depend directly on `sqlglot` expressions. This keeps the parser replaceable if we later need deeper PostgreSQL coverage, live introspection, or a different parser.

The first parser intentionally focuses on common Phase 1 DDL:

- `CREATE TABLE`,
- column names and PostgreSQL types,
- `NOT NULL`,
- defaults,
- inline primary keys,
- table-level composite primary keys,
- inline and table-level unique constraints,
- inline and table-level foreign keys.

### Follow-Up Notes

- More advanced PostgreSQL features can be added as test-driven parser cases.
- Live PostgreSQL introspection in Phase 2 should map into the same schema contracts.
- Parser support should fail clearly rather than silently approximating unsupported DDL.

## Decision: use a dependency graph for generation order

### Question

How should DataBoom decide which table to generate first when schemas contain foreign keys?

### Answer

Build a relationship graph where referenced parent tables point to dependent child tables, then topologically sort that graph. This produces an order where parent rows exist before child rows need to reference them.

### Why This Matters

Foreign-key correctness is the core value of DataBoom. If a child table like `orders` is generated before its parent table `users`, the generator either has to guess IDs or fix data later. Both approaches are risky. A dependency graph makes the correct order explicit before generation starts.

### Details

The graph treats normal foreign keys as parent-to-child dependencies. For example, `users.account_id -> accounts.id` means `accounts` must be generated before `users`.

Self-references are different. A table like `categories` may contain `parent_id` pointing back to `categories.id`. That should not block the whole table from being generated, so self-reference edges are recorded but ignored for cross-table dependency ordering. Later row generation can handle self-references within the table.

Cross-table cycles are not ignored. If table `a` requires table `b` and table `b` requires table `a`, generation needs a more advanced strategy. Phase 1 should fail clearly instead of producing invalid data.

### Follow-Up Notes

- Relationship solving will later use graph edges to choose valid foreign-key values.
- Self-referential row generation needs its own strategy when the generator reaches that feature.
- Cycles can be revisited later with deferred constraints or multi-pass generation if the product needs it.

## Decision: derive deterministic random streams from named namespaces

### Question

How should DataBoom make generated datasets reproducible without forcing every generator to share one global random object?

### Answer

Use a root seed and derive independent child seeds for named namespaces such as table names, column names, and generation steps. Each namespace can create its own `random.Random` stream while still being reproducible from the same root seed.

### Why This Matters

A single global random stream is fragile. If one generator starts consuming one extra random value, every generator after it changes output. Named child streams reduce that coupling. For example, changing how `users.email` is generated should not automatically change unrelated `orders.amount` values.

### Details

The seed manager uses SHA-256 over a stable JSON payload instead of Python's built-in `hash()`. Python intentionally randomizes `hash()` between processes for security, so using it for deterministic generation would make test data change between runs.

The output of the seed manager is still ordinary Python randomness; the important part is that every stream starts from a stable, reproducible seed.

### Follow-Up Notes

- Row generators should request streams through `SeedManager` instead of importing or mutating global `random`.
- Benchmarks should always record the root seed.
- If strict cross-language reproducibility is needed later, we may need a specified random algorithm instead of Python's default `random.Random`.

## Decision: create a generation plan before producing rows

### Question

Why should DataBoom build a generation plan instead of immediately generating rows from a schema and row-count dictionary?

### Answer

The plan separates "what should be generated" from "how rows are produced." It gives the engine a reviewable contract containing table order, row counts, column strategies, foreign-key sources, seed, and output formats.

### Why This Matters

Without a plan, generation logic would mix schema interpretation, dependency ordering, row counts, prompt interpretation, and output choices in one place. That would make later LLM-assisted planning risky because the LLM would have no safe structured target. A plan lets local deterministic logic and future LLM planning produce the same kind of object before execution.

### Details

The first plan builder is deterministic and schema-driven. It uses the relationship graph for table order, resolves row-count overrides, and marks columns as:

- primary keys,
- foreign keys,
- default-backed fields,
- generated fields.

This gives later row generation a simple job: execute the plan. It also gives dry-run mode a natural output in Phase 2 or Phase 3.

### Follow-Up Notes

- LLM-assisted planning should produce or modify this contract, not bypass it.
- CLI and API dry-run endpoints can expose this plan before generation.
- Validation should compare generated artifacts against the plan.

## Decision: start primitive generation with deterministic custom values

### Question

Why does primitive generation use fast custom deterministic values instead of calling Faker for every generated cell?

### Answer

Phase 1 should prioritize correctness, determinism, and throughput. Faker remains useful for richer realism later, but per-cell Faker calls can become expensive at 100k to 500k records. The first primitive generator uses type-family-specific deterministic logic so the row pipeline can scale before realism is expanded.

### Why This Matters

The hardest Phase 1 problem is not producing one fake email. It is producing many rows across related tables without breaking constraints or running out of time and memory. Fast primitive generators let us focus on the engine path: plan execution, primary keys, foreign keys, streaming exports, and validation.

### Details

The primitive generator currently handles:

- numeric values,
- booleans,
- datetimes,
- UUIDs,
- JSON-like dictionaries,
- string heuristics for emails, phones, names, statuses, and generic text.

It rejects foreign-key columns because those values must come from the relationship solver, not independent random generation.

### Follow-Up Notes

- Faker can be introduced behind strategy-specific generators once the engine pipeline is stable.
- Performance benchmarks should compare richer Faker-backed strategies with the custom fast path.
- Domain realism should be added without sacrificing deterministic seeds.

## Decision: store generated parent keys instead of full parent rows

### Question

How should child rows choose valid foreign-key values without keeping every generated parent row in memory?

### Answer

Store only generated parent key tuples in a foreign-key registry. Child tables can then choose from valid parent keys while the engine avoids retaining complete parent rows.

### Why This Matters

For 100k, 500k, and eventually 1M records, storing full rows for every table would waste memory. Foreign-key generation usually needs only the referenced key columns, not every parent field. A compact key registry supports relationship correctness while keeping the path open for streaming exports.

### Details

The row generator executes tables in dependency order from the generation plan. As each parent row is produced, the registry records its primary-key tuple. When a child row needs a foreign key, it picks a deterministic parent tuple from the registry and maps the tuple back onto the child columns.

This also supports composite keys. For example, `(tenant_id, user_id)` is chosen as one tuple, so the child row does not accidentally combine `tenant_id` from one parent with `user_id` from another.

### Follow-Up Notes

- The current registry stores primary-key tuples. Later phases may need indexes for foreign keys that reference unique non-primary columns.
- Very large parent key sets may need memory-aware sampling or disk-backed key registries.
- Exporters should consume generated rows sequentially so the engine does not need to materialize all rows at once.

## Decision: stream local CSV and SQL artifacts table by table

### Question

How should Phase 1 write generated datasets to disk without holding the whole dataset in memory?

### Answer

Export one table at a time and write each row directly to CSV and SQL files as it is generated. Keep only the small manifest and the foreign-key registry in memory.

### Why This Matters

The 100k-record Phase 1 target is much easier to reach if generated rows flow through the engine like a pipeline. Building a giant list of rows first would make memory grow with dataset size and would delay writing until the end of a run. Streaming makes output visible earlier and keeps the design compatible with larger runs.

### Details

The local exporter creates:

- one CSV file per table,
- one SQL insert file per table when requested,
- a manifest describing table artifacts and row counts.

It consumes `RowGenerator` sequentially by table. That preserves dependency order and lets the generator register parent keys before child rows are produced.

### Follow-Up Notes

- Validation should read the manifest and artifact files instead of depending on in-memory rows.
- Future SQL export can batch inserts or use PostgreSQL `COPY` for better load performance.
- Object storage can be added later behind a separate artifact storage boundary.

## Decision: validate exported artifacts instead of in-memory rows

### Question

Should validation check rows before export, or should it validate the artifact files that users will actually consume?

### Answer

Phase 1 should validate exported artifacts. The validator reads the manifest and CSV files, then checks row counts, required values, primary-key uniqueness, and foreign-key integrity.

### Why This Matters

Validating in-memory rows can miss problems introduced during serialization or file writing. Users care whether the CSV and SQL artifacts are loadable and consistent, so the validation path should inspect the files produced by the exporter.

### Details

The current validator uses CSV artifacts for content checks because CSV is easy to inspect and parse. It verifies that generated child keys exist in parent key sets and that primary keys are unique in each table. This gives Phase 1 a practical correctness loop without needing a live database load yet.

### Follow-Up Notes

- Later phases should add direct PostgreSQL load validation.
- SQL-only exports currently receive path and manifest checks, but deeper SQL parsing can come later.
- Privacy validation belongs in Phase 4 once privacy policies exist.

## Decision: establish a Phase 1 100k-record benchmark baseline

### Question

How do we know the Phase 1 engine can generate the target 100k records without relying on guesses?

### Answer

Add a repeatable benchmark script that generates 100k records across related tables, exports CSV artifacts, validates the result, and records elapsed time, peak memory, artifact size, and validation status.

### Why This Matters

Performance goals need measurements. A benchmark gives us a baseline before optimization work, and it prevents future changes from accidentally making generation much slower or more memory-heavy.

### Details

The first measured run in this environment generated 100k records across `accounts`, `users`, and `orders`.

Measured result:

- records: 100,000,
- tables: 3,
- elapsed time: 44.691 seconds,
- peak memory: 50.71 MB,
- artifact size: 5.312 MB,
- validation: passed.

This is good enough for a Phase 1 baseline, but it also shows where performance work can improve later. The engine is already memory-bounded reasonably because it streams artifacts and stores key tuples instead of full parent rows.

### Follow-Up Notes

- The benchmark should be rerun after row generation, export, validation, or serialization changes.
- Phase 2 should target 500k records and compare memory growth against this baseline.
- Optimization should focus on hot paths only after profiling, not before.

## Decision: use domain profiles as semantic overlays

### Question

How should DataBoom support use cases like financial data, banking data, healthcare patients, and future domains without turning the core generator into a pile of hard-coded column checks?

### Answer

Use domain profiles as semantic overlays. The generic engine still owns schema parsing, planning, relationships, seeding, exporting, and validation. Domain providers only improve values for columns they understand, then fall back to the generic generator for everything else.

### Why This Matters

Different users need different kinds of realism. A banking team cares about account types, transaction statuses, currencies, balances, and merchants. A healthcare team cares about medical record numbers, diagnosis codes, blood types, vitals, and insurance providers. These should not require separate engines.

### Details

The first profiles are:

- `general`: generic type-family generation,
- `financial`: financial and banking semantics,
- `healthcare`: patient and clinical semantics.

This keeps the engine extensible: a future `retail`, `education`, `logistics`, or `telecom` profile can be added as another provider without changing the relationship solver or exporter.

### Follow-Up Notes

- Domain profiles should remain deterministic through `SeedManager`.
- Profiles should never override foreign keys; relationships still come from the solver.
- Richer domain realism can later come from configuration files or prompt-planned column strategies.

## Commit: backend: scaffold python package and settings

### What Changed

- Added `pyproject.toml` with the Python package metadata, runtime dependencies, dev dependencies, pytest configuration, Ruff configuration, and the `databoom` CLI entry point.
- Added `.gitignore` so local virtual environments, caches, build outputs, coverage files, environment files, and generated artifacts do not get committed accidentally.
- Added `.env.example` to document the first environment variables.
- Created the initial `src/databoom` package layout.
- Added `databoom.cli` with an `info` command that prints active configuration.
- Added `databoom.core.config` with Pydantic settings for environment, artifact root, and log level.
- Added `databoom.core.logging` for shared logging setup.
- Added `databoom.core.artifacts` for local artifact directory creation.
- Added `tests/test_config.py` to verify settings normalization and artifact path resolution.

### Why It Changed

Phase 1 needs a stable Python backend foundation before schema parsing, relationship solving, generation, and validation can be added. Without the package layout, dependency declaration, settings model, and test runner, later features would be built on loose scripts instead of a maintainable backend.

### Why This Approach

The project uses a `src/` layout because it prevents tests from accidentally importing files from the repository root in ways that differ from an installed package. This catches packaging mistakes earlier.

Pydantic settings are used because DataBoom will eventually run as both a CLI and an API service. Both entry points need the same validated configuration. Starting with settings now avoids scattering environment variable reads throughout the codebase.

The artifact helper is intentionally tiny. Phase 1 and Phase 2 store output on local disk, so the first abstraction only creates and resolves the artifact root. More complex storage adapters can wait until object storage is actually needed.

### Performance, Reliability, or Maintainability Impact

This commit does not add data generation performance yet. It improves reliability by making configuration typed and testable. It improves maintainability by giving future modules a predictable place to live and by making tests run through standard pytest discovery.

The `.gitignore` also protects performance work later: large generated artifacts should stay on disk locally, not enter git history.

### Beginner Explanation

This commit builds the empty workshop before building the machine. The package directory is where the engine code will live, the settings file is where runtime knobs are read, the artifact helper is where generated files will be stored, and the test file proves the first small pieces behave correctly.

### Follow-Up Notes

- Schema model contracts come next.
- Docker and Compose should be committed separately as infrastructure.
- Redis will be available in Compose for future run coordination, but Phase 1 code should not depend on it yet.

## Decision: start the frontend as an operational workbench

### Question

Should the first frontend be a marketing-style landing page, or should it behave like the first visible shell of the data generation product?

### Answer

Start with an operational workbench. The first screen should show generation configuration, domain profiles, output formats, validation status, benchmark context, and demo datasets even before the backend API is wired in.

### Why This Matters

DataBoom is an engine product. Users need confidence that it can plan, generate, export, and validate datasets. A landing page might look polished, but it would not teach us much about the real product workflow. A workbench layout gives the backend phases a visible target and keeps frontend work aligned with generation capability.

### Details

The frontend is built with Next.js, TypeScript, Tailwind CSS, and lucide-react icons. Tailwind keeps styling consistent without handwritten raw CSS, while small reusable components keep the interface ready for API integration.

The static Phase F1 shell intentionally mirrors the backend concepts already implemented:

- domain profiles for general, financial, and healthcare generation,
- output formats for CSV, JSON, and SQL,
- the generation pipeline from schema parsing through validation,
- benchmark and validation status,
- demo datasets generated by the engine.

This makes future phases straightforward. Phase F2 can replace static values with FastAPI responses. Phase F3 can turn the schema and domain areas into real editors. Phase F4 can add LLM-assisted planning without redesigning the screen from scratch.

### Follow-Up Notes

- Keep frontend phases documented in `docs/frontend-development.md`.
- Avoid building disconnected decorative pages until the workbench flow is useful.
- When API endpoints arrive, preserve the same component boundaries and wire data through typed interfaces.

## Decision: stage relational, document, and graph data support by phase

### Question

Should DataBoom try to support relational databases, NoSQL documents, and graph data all at once?

### Answer

No. The roadmap should keep PostgreSQL relational generation in Phase 1, add NoSQL document data in Phase 2, and add graph data in Phase 3.

### Why This Matters

Each data family has different correctness rules. Relational data depends on tables, primary keys, foreign keys, and dependency ordering. Document data depends on nested shapes, arrays, object identifiers, and optional references. Graph data depends on nodes, edges, labels, properties, and cardinality. Combining all of that too early would make the engine harder to validate and harder for new contributors to understand.

### Details

Relational generation is first because it proves the hardest foundational engine behavior: parse a schema, compute dependency order, preserve references, stream artifacts, and validate the result. Once that is stable, Phase 2 can add NoSQL document generation on top of the same planning, artifact, and validation ideas, but with document-specific contracts. Phase 3 can then add graph data once the planner and operator review experience are strong enough to explain node and edge plans before execution.

This also keeps the frontend roadmap honest. The visible roadmap should move major shipped capabilities into achieved steps, while future data-family work remains visible as upcoming milestones.

### Follow-Up Notes

- Phase 2 should start with JSON/NDJSON and MongoDB-style nested records before claiming broad NoSQL coverage.
- Phase 3 graph support should start with node and edge artifacts before deeper database-specific graph adapters.
- Privacy and policy enforcement still belong later, after the generation paths are reliable.

## Decision: expose Phase 2 API through an app factory

### Question

How should the first FastAPI code be introduced without tangling API concerns into the existing CLI?

### Answer

Use a dedicated `databoom.api` package with a `create_app()` factory, typed response models, and small system routes for `/health` and `/ready`.

### Why This Matters

The API will soon own generation run creation, run status, artifact downloads, and validation report access. Starting with an app factory gives tests and deployment code a clean way to construct the service with explicit settings. It also keeps the CLI as a local workflow instead of making it responsible for HTTP behavior.

### Details

The app stores the active `Settings` object on `app.state`, then routes can read the same configuration the CLI already uses. The first endpoints intentionally return runtime context only: service name, version, environment, and resolved artifact root. This proves the API can be tested and configured before adding long-running generation endpoints.

The test suite uses FastAPI's `TestClient`, which currently requires the `httpx2` package in this environment, so `httpx2` is declared as a development dependency.

### Follow-Up Notes

- Next API work should add generation run request and status models.
- Artifact download endpoints should reuse the existing manifest and validation report structure.
- The frontend roadmap should list significant Phase 2 API milestones as achieved when they land.

## Decision: start API generation runs synchronously

### Question

Should the first API generation endpoint introduce background workers, queues, Redis state, and async orchestration immediately?

### Answer

No. The first `/runs` endpoint should execute a local relational generation run synchronously, write artifacts to local disk, and store the run response in the current API process.

### Why This Matters

The existing engine already generates and validates local artifacts. The next backend risk is the HTTP contract: request shape, status response, artifact paths, validation summary, error handling, and frontend integration. A synchronous endpoint proves that contract without adding queue complexity too early.

### Details

The endpoint accepts PostgreSQL DDL, row counts, seed, domain profile, and output formats. It reuses the same parser, planner, exporter, and validator as the CLI. Artifacts are written under `artifacts/runs/{run_id}` so API runs do not collide with CLI or benchmark outputs.

The in-memory run store is intentionally temporary. It makes `POST /runs`, `GET /runs`, and `GET /runs/{run_id}` useful during local development, but it is not the final production run-state design. Later Phase 2 work can replace it with persistent metadata and background execution without changing the basic response contract.

### Follow-Up Notes

- Add artifact download endpoints before asking the frontend to download files.
- Add persistent run state before long-running or multi-worker deployment.
- Add background execution only when progress reporting, cancellation, retries, or large runs require it.

## Decision: wire the frontend to the local API with a small bridge

### Question

How much frontend/API integration should happen before the full generation dashboard exists?

### Answer

Start with a small client-side API bridge that checks `/health`, lists `/runs`, and can create a tiny demo run through `POST /runs`.

### Why This Matters

This proves that the frontend and backend can communicate through the real HTTP contract while keeping the UI surface small. It also keeps the product roadmap honest: the API achievement is visible, and a user can trigger a real backend run from the workbench instead of only seeing static mock data.

### Details

The bridge defaults to `http://localhost:8000` and can be configured with `NEXT_PUBLIC_DATABOOM_API_URL`. It intentionally uses a tiny built-in schema so local demo runs finish quickly and do not require file upload UI yet.

This is not the final generation workflow. Later Phase 2 screens should let users paste or upload DDL, choose row counts, select formats, review validation, and download artifacts. The bridge is a low-risk step that verifies connectivity and response contracts first.

### Follow-Up Notes

- Add artifact download endpoints before building download buttons.
- Move the demo schema into backend fixtures or examples if it starts being reused in multiple places.
- Add better error states once API authentication and persistent run storage arrive.

## Decision: expose run artifacts through path-safe API endpoints

### Question

Why add artifact listing and download endpoints before building a richer run dashboard?

### Answer

The API already creates local artifacts, but a client cannot use them unless it can discover and retrieve files through HTTP. Adding `GET /runs/{run_id}/artifacts` and `GET /runs/{run_id}/artifacts/{relative_path}` closes that loop for local runs without introducing a queue, worker, object storage, or authentication system before those pieces are truly needed.

### Why This Matters

This turns a generation run into a complete API workflow: create a run, read its status, list its outputs, and download the files. That is the minimum contract the frontend, CLI automation, and future integrations need before they can offer artifact download buttons or pipeline handoffs.

### Security and Reliability Detail

The download endpoint resolves the requested path against the specific run's artifact directory and rejects paths that escape that directory. This prevents a request such as `../secret.txt` from reading unrelated files on disk. Even though Phase 1 and early Phase 2 are local-development focused, this is a production-grade habit worth adding early because artifact APIs are naturally file-system adjacent.

The endpoint still uses the in-process run store, so it only knows about runs created by the current API process. That is acceptable for this phase. Persistent run metadata should come before multi-worker deployment, API restarts, or long-running background generation.

### Follow-Up Notes

- Add authentication before exposing artifact downloads beyond a trusted local environment.
- Add persistent run metadata so artifacts survive API process restarts.
- Add retention policies before artifact storage can grow without bounds.

## Decision: make API-key authentication opt-in for run routes

### Question

How should authentication enter the project without making local development painful?

### Answer

Add `DATABOOM_API_KEY` as an optional setting. When it is absent or empty, the API behaves like the current local developer service. When it is set, generation run and artifact routes require the `X-API-Key` header. Health and readiness remain open so Docker, orchestration tools, and uptime checks can still verify that the service is alive.

### Why This Matters

The project is still early, but run creation and artifact downloads already touch local files and generate data. Protecting those routes behind a simple shared secret is a pragmatic production-grade step before the service grows into background jobs, persisted run metadata, and downloadable artifacts in a deployed environment.

### Implementation Detail

The key comparison uses constant-time comparison through `secrets.compare_digest`, which avoids leaking information through simple timing differences. Empty environment values are normalized to `None`, so copying `.env.example` does not accidentally require an empty `X-API-Key` header.

This is not the final authorization model. Later phases can add users, projects, scoped tokens, audit logs, and per-artifact policies. The important choice right now is the boundary: system health is public, while anything that creates or retrieves generated data can be protected.

### Follow-Up Notes

- Add scoped API tokens before multi-user deployment.
- Add audit logging before artifact downloads are exposed in shared environments.
- Make the frontend send an API key only after the product has a safe local settings pattern.

## Decision: split CLI planning and validation from generation

### Question

Why add separate `plan` and `validate` commands when `generate` already creates artifacts and validates them?

### Answer

Separate commands make the backend workflow easier to inspect and automate. `databoom plan` lets a user or CI job review the exact table order, row counts, column strategies, dependencies, seed, domain, and output formats before any files are generated. `databoom validate` lets a user re-check an artifact directory later without spending time regenerating data.

### Why This Matters

Large synthetic datasets are expensive enough that repeatability matters. If a 100k or 500k record run already exists, a developer should be able to validate the outputs after moving files, changing tests, or debugging a failed load step. Likewise, plan preview gives future LLM-assisted planning a stable target: whether a human or model proposes a plan, the engine can expose a structured, reviewable contract before execution.

### Implementation Detail

The exporter now has a small `load_export_manifest()` function. That keeps validation tied to the same manifest format written during generation instead of duplicating file discovery logic in the CLI. The CLI rebuilds the expected generation plan from the schema and options, loads `manifest.json`, then runs the same validator used by `generate`.

This is intentionally not a full saved-plan system yet. A future phase can persist plan JSON and validate directly from that file. For now, schema plus options are enough to keep the command simple and compatible with the current engine.

### Follow-Up Notes

- Add `--plan-path` support once saved plans become part of the public workflow.
- Add richer validation output formats for CI, such as JSON-only output.
- Make validation chunk-aware before pushing much beyond the current Phase 1 dataset sizes.

## Decision: add live PostgreSQL introspection as a library boundary first

### Question

Why implement live database introspection before exposing a full API or CLI workflow for it?

### Answer

The risky part is translating real PostgreSQL metadata into the same normalized `DatabaseSchema` contract used by DDL parsing. By adding `load_postgres_schema()` and `inspect_postgres_schema()` first, the engine can support live schemas without forcing a new user workflow before the underlying contract is proven.

### Why This Matters

DDL files are useful for Phase 1, but many teams keep the source of truth in a running database. Live introspection lets the project read tables, columns, primary keys, foreign keys, unique constraints, defaults, nullability, identity information, and common PostgreSQL type details from SQLAlchemy's inspector. Once that normalized model exists, the existing planner and generator can reuse it instead of maintaining a separate path for database-backed workflows.

### Implementation Detail

The introspection function accepts a SQLAlchemy connectable for tests and an external `database_url` helper for real use. Tests use a fake inspector instead of requiring Docker or a live database, which keeps the suite fast and deterministic while still validating the metadata mapping.

The helper disposes the SQLAlchemy engine after loading schema metadata. That matters for production-grade behavior because database connections should not linger after one-shot metadata reads.

### Follow-Up Notes

- Add CLI/API commands that call `load_postgres_schema()` once the workflow shape is clear.
- Add integration tests against the Docker PostgreSQL service when CI infrastructure is ready.
- Extend type mapping as real-world schemas reveal more PostgreSQL-specific types.

## Decision: rename the product and package surface to DataBoom

### Question

Why rename the repository's public surface from Boom Data to DataBoom?

### Answer

DataBoom works better as the parent platform name because it can hold multiple products without making every feature sound like the same single engine. The code package, CLI command, environment prefix, Docker defaults, frontend metadata, and documentation now use `databoom`/`DATABOOM`/`DataBoom` consistently.

### Why This Matters

Naming is architecture when a product is becoming a platform. A single generic name was fine while the project was only a generator, but the roadmap now has two large product families: generation and masking. DataBoom gives those families a shared umbrella while leaving space for whacky product names below it.

### Implementation Detail

The Python package moved from `src/boom_data` to `src/databoom`, the CLI script moved from `boom-data` to `databoom`, and configuration now reads `DATABOOM_` environment variables. The workspace folder itself is still `/home/odoo/boom-data` so the active development session and git checkout are not disrupted.

### Follow-Up Notes

- Update any external scripts that still invoke `boom-data`.
- Reinstall the editable package after pulling this change so `.venv/bin/databoom` is available.
- Keep product-family naming separate from engine internals so sub-products do not leak into every module name.

## Decision: standardize the DataBoom product catalog

### Question

How should DataBoom explain its product family without turning every demo domain into a separate product?

### Answer

Use DataBoom as the parent platform with four catalog products: Table-Boom for relational data, Docu-Boom for NoSQL document data, Graph-Boom for graph data, and Masker-Boom for future privacy-preserving masking and redaction.

### Why This Matters

Product names should describe the actual engine surface. Relational tables, document collections, graph nodes/edges, and masking policies require different contracts, previews, validation, and exports. Banking, healthcare, ecommerce, SaaS, insurance, and similar categories change examples and domain profiles, but they should not create separate product branches.

This keeps the catalog memorable without blurring scope. Table-Boom can power financial or healthcare relational demos. Docu-Boom can power nested commerce, event, or customer-profile document demos. Graph-Boom and Masker-Boom stay visible in the roadmap without pretending they are implemented before their phases.

### Implementation Detail

The docs now include a dedicated `docs/product-family.md` file as the canonical taxonomy. README, functional specs, technical roadmap, prompt caching notes, frontend plan, agent instructions, and frontend copy all point back to that product map. Demo folders use use-case names such as `demo/financial-relational` and `demo/healthcare-relational`.

The code still keeps boring package and enum names such as `databoom`, `financial`, and `healthcare`. That is intentional. Whacky product names belong in user-facing docs and UI; stable internal names make APIs and tests easier to maintain.

### Follow-Up Notes

- Add a future `databoom.masking` package only when Masker-Boom implementation starts.
- Keep README product tables updated as modules move from planned to active.
- Avoid claiming Masker-Boom exists as a working masking engine until Phase 4 code lands.

## Decision: add a long-running Docker Compose API service

### Question

Why add a dedicated `api` service instead of only using the existing Docker tool container?

### Answer

The previous Compose setup could start PostgreSQL and Redis and run the app image as a one-shot CLI tool, but it did not expose the FastAPI service as a long-running container. A Dockerized setup should let a developer run `docker compose up -d --build` and immediately reach the API at `/health`.

### Why This Matters

Deployment readiness is one of the project goals. A container image that only prints `databoom info` is useful for smoke checks, but it does not prove the HTTP app can run with Compose-managed dependencies. The new `api` service runs Uvicorn, mounts local artifacts, waits for PostgreSQL and Redis health checks, exposes port `8000`, and has its own health check.

### Implementation Detail

The host port can be overridden with `DATABOOM_API_PORT`, for example `DATABOOM_API_PORT=8001 docker compose up -d --build`. This avoids a common local-development failure when another API server already uses port `8000`.

PostgreSQL and Redis host ports are configurable too: `DATABOOM_POSTGRES_PORT` and `DATABOOM_REDIS_PORT`. The containers still talk to each other on `postgres:5432` and `redis:6379` inside the Docker network, but developers can map those services to alternate localhost ports when their machine already has PostgreSQL or Redis running.

The `app` service remains under the `tools` profile so it can still be used for CLI-oriented container runs without becoming part of the default long-running stack.

### Follow-Up Notes

- Add a production image stage before a public release.
- Add API-key configuration to Compose examples once the auth story is ready for shared environments.
- Add a frontend container only when the frontend needs Dockerized deployment, not just local development.

## Decision: copy package metadata into the Docker image before install

### Question

Why did the Docker build fail at `python -m pip install .` even though the source code was copied?

### Answer

The package configuration declares `README.md` as the project readme in `pyproject.toml`. Python build backends validate that metadata while preparing the wheel. The Dockerfile copied `pyproject.toml`, `instructions.md`, and `src`, but it did not copy `README.md`, so Hatchling correctly stopped the build with `OSError: Readme file does not exist: README.md`.

### Why This Matters

Docker images should build from the same packaging contract that local installs use. If the image skips metadata files, the container can fail even when the Python modules themselves are present. Keeping packaging metadata in the image also catches broken release metadata earlier, which is useful before CI/CD and deployment automation become stricter.

### Implementation Detail

The Dockerfile now copies `README.md` together with `pyproject.toml` and `instructions.md` before running `pip install .`. This keeps Docker layer caching efficient: dependency and metadata changes invalidate the install layer, while ordinary source changes only invalidate the later source copy and install step.

### Follow-Up Notes

- If future package metadata references `LICENSE`, changelog files, or generated assets, copy those files before `pip install .` too.
- Consider adding a CI job that runs `docker compose build api` so packaging regressions are caught before local deployment testing.

## Decision: make the local full-stack path actually exercise backend output

### Question

Why show generated tables and artifact downloads in the frontend instead of only showing API health and run counts?

### Answer

A full-stack app should prove that the user action travels through the browser, reaches the backend, runs the engine, writes artifacts, validates them, and returns useful output. Health checks prove the server is alive, but they do not prove the product workflow works.

### Why This Matters

DataBoom's core promise is not just "an API exists." The promise is that Table-Boom and Docu-Boom can produce usable synthetic datasets for their data surfaces. By showing generated table names, row counts, validation status, and artifact download links in the hero control center, the frontend now demonstrates the real product path with the current Phase 1/2 backend capabilities.

This also keeps frontend work aligned with backend phases. The current UI still uses a small built-in schema so it remains fast and reliable, but the same shape can later support pasted DDL, row-count controls, domain selection, output-format switches, async run status, and detailed validation reports.

### Implementation Detail

The `ApiRunPanel` now calls `POST /runs`, then calls `GET /runs/{run_id}/artifacts` for the generated files. It renders the latest run's tables and backend-provided artifact download URLs. This keeps the frontend from guessing file names or duplicating artifact-layout rules that belong to the API.

The backend settings layer now reads explicit `DATABOOM_*` variables through validation aliases, and CORS origins are configurable with `DATABOOM_CORS_ORIGINS`. That matters in local development because the frontend may run on `3000` or `3001`, and Dockerized backend ports may move when a laptop already has services on `8000`, `5432`, or `6379`.

### Follow-Up Notes

- Add frontend controls for pasted schema, row counts, domain profile, and output formats.
- Add detailed validation report rendering instead of only pass/fail.
- Move API runs to persisted storage before relying on run history across container restarts.
- Add async/background run execution before increasing default browser-triggered runs toward 500k records.

## Decision: promote the UI from demo bridge to product dashboard

### Question

Why add login, subscriptions, product-run endpoints, and run detail pages before building more generator internals?

### Answer

The project needs to feel like a product, not only an engine with a button. A user should be able to enter the app, choose a product module, subscribe to it, generate data, inspect output, and download artifacts. That path is now represented end to end with real frontend pages and real backend endpoints.

### Why This Matters

Full-stack product confidence comes from seeing state move through system boundaries. If subscription and product generation only lived as frontend mock state, the dashboard would look nice but would not prove the backend can support the workflow. By adding backend product catalog, demo auth, subscriptions, product-specific run creation, and table previews, the UI now exercises the same FastAPI service that generates and serves artifacts.

This also sets up the commercial product model early. DataBoom can have many modules, but each one needs a consistent lifecycle: discover product, subscribe, configure, generate, preview, download, and audit. Even with demo credentials and in-memory subscriptions, the route shape is close to the production shape.

### Implementation Detail

The backend owns runnable product definitions in `src/databoom/api/products.py`. Each catalog entry includes schema DDL, default row counts, output formats, a domain profile, features, and plans. The product-run endpoint turns that catalog entry into a normal `GenerationRunRequest`, so it reuses the existing parser, planner, generator, exporter, and validator instead of creating a second generation path.

The table preview endpoint reads the generated CSV artifact for a selected table and returns the first rows as structured JSON. This is better than making the frontend guess artifact file paths or parse downloaded files by itself. The frontend can render collapsible top-10 previews while the backend remains the source of truth for artifact layout.

The frontend now has dedicated pages:

- `/` for the public hero/product story,
- `/login` for demo authentication with `demo` / `demo`,
- `/dashboard` for subscriptions and recent runs,
- `/products` for the product catalog,
- `/products/[productId]` for subscribing and generating,
- `/runs` for run history,
- `/runs/[runId]` for table previews and downloads,
- `/roadmap` for visible phase progress.

The public route stays separate from the authenticated console. This mirrors mature product sites: the homepage explains value, product families, use cases, and trust signals, while the logged-in workspace owns operational workflows. In DataBoom terms, `/` explains Table-Boom, Docu-Boom, Graph-Boom, and Masker-Boom, then `/dashboard` becomes "My Dashboard" for subscribed product work.

The app shell brand now links back to `/` because the DataBoom logo is a product-home affordance, not a dashboard-only navigation item. Subscription details moved from the dashboard into `/settings/subscriptions`; this keeps the dashboard focused on operational status and recent runs while settings owns account/module state. The public header checks the local demo session before showing login actions, so logged-in users see "My dashboard" instead of a confusing login CTA.

### Follow-Up Notes

- Replace demo auth with real auth before shared deployment.
- Persist sessions, subscriptions, and run metadata in PostgreSQL instead of app memory.
- Move long-running generation to a job queue before allowing large dashboard-triggered runs.
- Add custom schema upload and saved generation templates once the dashboard flow is stable.

## Decision: persist API state behind a store boundary

### Question

Why move demo sessions, product subscriptions, and generation-run metadata out of FastAPI app dictionaries before building more dashboard features?

### Answer

The dashboard has crossed from a static demo into a real full-stack workflow. Once a user can log in, subscribe, generate data, preview tables, and download artifacts, that workflow should not disappear whenever the API process restarts. A small persistence layer gives the product a durable backbone while keeping the current routes and frontend contract stable.

### Why This Matters

In-memory dictionaries are useful for the first proof of concept because they are simple and fast. They are not good enough for a product console. If the API container restarts after a user generates data, the artifact files may still exist on disk, but the API would forget the run ID, product subscription, and session token. That breaks the user's path through the app even though the engine did its work correctly.

PostgreSQL is already part of the DataBoom stack, so storing API metadata there is the natural next step. This improves reliability without introducing a queue, workflow engine, or heavy orchestration system before the project needs one.

### Implementation Detail

The backend now has a `StateStore` protocol. Routes call methods such as `save_session()`, `list_subscriptions()`, and `save_run()` instead of reading and writing raw dictionaries. There are two implementations:

- `MemoryStateStore` keeps tests and fallback local development lightweight.
- `SQLAlchemyStateStore` stores JSON payloads for demo sessions, subscriptions, and generation runs in SQL tables.

This design keeps SQLAlchemy out of route business logic. A route should care about product behavior: authenticate, subscribe, generate, preview, download. It should not know table names or write SQL statements inline. That separation makes the backend easier to change later when the metadata model becomes more normalized.

For the MVP, run payloads are stored as JSON. That is a practical bridge: the API already has typed Pydantic response models, and storing their JSON form preserves the current contract with minimal code. Later, high-query fields such as run status, product ID, owner, artifact root, duration, row counts, and validation status can be promoted into first-class columns.

### Performance, Reliability, or Maintainability Impact

Reliability improves because Dockerized API runs can survive process restarts while keeping sessions, subscriptions, and run metadata. Maintainability improves because persistence is now a replaceable boundary instead of a pattern duplicated across endpoints.

The performance impact is intentionally small for the current scale. Sessions, subscriptions, and run metadata are tiny compared with generated datasets. The large files still live on local disk under `artifacts/`, so PostgreSQL is not being used as a blob store. That keeps the database focused on metadata and leaves bulk generated data in file artifacts where Phase 1 and Phase 2 can inspect it easily.

### Beginner Explanation

Think of generated CSV/JSON/SQL files as packages in a warehouse. The API metadata is the clipboard that says which packages exist, who requested them, and where to find them. Before this change, the clipboard was wiped whenever the API restarted. Now the clipboard is saved in PostgreSQL.

The `StateStore` is like a service desk window. The rest of the app asks the window for sessions, subscriptions, and runs. Today the window can talk to memory or PostgreSQL. Later it can talk to a more advanced database design without forcing every route to be rewritten.

### Follow-Up Notes

- Replace `metadata.create_all()` with Alembic migrations before production deployment.
- Normalize important run fields into columns when filtering, search, ownership, or dashboards become more advanced.
- Add real user accounts and authorization before shared deployment.
- Move long-running generation into background jobs before dashboard-triggered large runs become common.
- Add artifact retention and cleanup rules so persisted run metadata cannot point to deleted files without an explicit status.

## Decision: make the authenticated dashboard a reusable data workspace

### Question

Why replace the card-style dashboard with a database-console layout inspired by tools like Tonic Fabricate?

### Answer

The authenticated app should feel like a place where users inspect generated data, not just a page that reports counts. The workspace uses a three-panel workflow: product and resource navigation on the left, data preview in the center, and an agent/run panel on the right.

### Why This Matters

Synthetic data products become easier to trust when users can immediately inspect the output. A run count is abstract. A table grid with columns, inferred types, row previews, validation status, generation steps, and export links is concrete. It proves that the backend generated real artifacts and that the frontend can browse them.

This layout also maps better to how data users think. Relational users expect databases, tables, records, SQL/JSON/CSV exports, and summaries. Document users expect collections, nested JSON, and JSON/NDJSON exports. Keeping those concepts visible makes the product feel closer to a production data tool and less like a marketing dashboard.

### Implementation Detail

The `DataWorkspace` component keeps the flow wired to the existing FastAPI backend:

- it loads products, subscriptions, and runs,
- it lets the user subscribe to a product,
- it generates a product run through `POST /products/{product_id}/runs`,
- it loads table or document previews through the preview APIs,
- it lists downloadable artifacts through the artifact API,
- it shows agent steps based on the selected run and validation state.

The UI does not claim to have a real LLM planner yet. The right panel uses agent-style language and a prompt box, but execution still goes through deterministic product defaults. That is intentional: the user experience can prepare for Phase 3 LLM-assisted planning without pretending that the backend planner exists today.

### Performance, Reliability, or Maintainability Impact

The workspace improves perceived performance because users can inspect top records instead of downloading full artifacts immediately. It also keeps large output constrained to scrollable preview areas, which avoids resizing the whole page when rows, columns, or documents are wide.

Maintainability improves because the workspace is componentized instead of embedded directly inside the dashboard page. The route now only handles authentication and delegates the product-specific operational UI to `DataWorkspace`.

### Follow-Up Notes

- Add run progress events once backend jobs become asynchronous.
- Add editable row-count and schema/spec controls inside the workspace when custom generation becomes the next focus.
- Add real prompt-to-plan behavior only after the planner interface and prompt cache strategy are implemented.
- Consider dedicated product routes only if the shared workspace becomes too constrained for graph or masking workflows.

## Decision: render products by data surface instead of domain product names

### Question

Should DataBoom keep separate product branches such as banking, healthcare, commerce, and similar domain names, or should it keep a smaller catalog organized by the shape of data being generated?

### Answer

Keep four catalog products based on data surface and workflow: Table-Boom for relational data, Docu-Boom for NoSQL document data, Graph-Boom for graph data, and Masker-Boom for masking/redaction. Banking, healthcare, ecommerce, SaaS, and similar names should be demo use cases or domain profiles under those products, not standalone products.

### Why This Matters

Product boundaries should match the engine behavior. Relational tables, JSON documents, graph nodes/edges, and masking policies need different runtime models, previews, validations, and export shapes. Banking versus healthcare usually changes the schema, labels, value generators, or examples, but it does not require a totally separate engine.

This keeps the project easier to scale. A new financial demo can reuse Table-Boom if it is relational. A healthcare document demo can reuse Docu-Boom if it is nested JSON. The frontend can show different surfaces by reading `product.kind` instead of hard-coding product IDs.

### Details

The backend catalog now exposes a stable `kind` for each product. The API can dispatch relational products to the existing table engine and document products to the Docu-Boom document generator. Planned graph and masking products stay visible in the catalog but return clear planned states until their runtime engines exist.

The frontend uses one generic workspace shell:

- relational products render resource navigation plus a spreadsheet-style table grid,
- document products render collection navigation plus MongoDB-style JSON cards,
- planned graph and masking products render planned-product states,
- artifacts, generation steps, run summaries, and validation status are shared wherever possible.

This is more maintainable than copying a dashboard for every product. If every use case had its own component and endpoint, the codebase would quickly contain duplicate subscription buttons, duplicate artifact lists, duplicate loading states, and duplicate run summaries. Shared workflow code makes future features easier to add and easier to test.

### Follow-Up Notes

- Table-Boom and Docu-Boom are active for local MVP workflows.
- Graph-Boom should add node/edge models and previews in Phase 3.
- Masker-Boom should add policy, redaction, tokenization, classification, and audit views in Phase 4.
- Phase 2 still needs formal 500k benchmark evidence and deeper structural profiling before production-scale claims are made.

## Decision: split docs and public site by concern

### Question

How should the project keep architecture docs and public website content understandable as the product grows?

### Answer

Split documentation into `docs/product`, `docs/engineering`, and `docs/operations`, then give architecture diagrams their own engineering document. Split the public website into real routes for home, products, demos, roadmap, and contact instead of keeping every marketing section in one scrolling page.

### Why This Matters

The docs folder was starting to mix product scope, technical architecture, frontend planning, prompt strategy, and usage commands at one level. That works for a tiny project, but it becomes noisy once the engine has multiple products and deployment concerns. A concern-based folder structure makes it obvious where a future contributor should place product strategy, architecture, or local run instructions.

The public website had a similar issue. A long single page made the landing page carry product catalog, pipeline explanation, roadmap, validation, demos, and dashboard links all at once. Standard product sites usually separate these concerns. The homepage should explain the core value quickly. Product details, demos, roadmap, and contact/evaluation content deserve their own routes.

### Details

The new architecture document explains DataBoom through several diagrams:

- system context,
- product surface model,
- engine pipeline,
- API run sequence,
- frontend route architecture,
- Docker deployment topology.

The key extensibility rule is that new products should branch by data surface through `product.kind`, not by demo domain or product name. The engine is extendable because each product kind can add its own spec/model, generator, validator, exports, and preview surface while sharing catalog resolution, seed management, artifacts, manifests, run metadata, and API download behavior.

On the frontend, public pages now share a public shell with launch bar, header, theme toggle, sections, and footer sitemap. Public pages support light and dark themes with CSS tokens. Authenticated dashboard pages remain focused on operational work.

### Follow-Up Notes

- Keep new docs inside the correct folder instead of recreating a flat docs directory.
- Add architecture diagrams when new product surfaces or deployment boundaries are introduced.
- Do not let public marketing pages duplicate authenticated dashboard workflows.

## Decision: establish a 500k Phase 2 benchmark baseline

### Question

Can Table-Boom currently generate and validate 500k relational records, and what does that reveal about the next optimization target?

### Answer

Yes. The new Phase 2 benchmark generated and validated 500,000 CSV records across five related tables. The baseline passed validation in this environment with 238.368 seconds total runtime, 224.239 seconds spent exporting, 14.105 seconds spent validating, 262.044 MB peak memory, and 35.96 MB of artifacts.

### Why This Matters

The project previously had a 100k benchmark, but Phase 2 explicitly needs evidence toward larger local runs. A 500k benchmark gives us a repeatable measurement point before optimizing. Without the baseline, we could easily optimize the wrong thing.

The numbers show that generation/export is currently the dominant runtime cost. Validation is much faster, but it still reads CSV artifacts into memory per table, so memory behavior should be hardened before moving toward million-record runs or background API jobs.

### Details

The benchmark uses a financial-style relational schema with customers, accounts, cards, transactions, and alerts. Those tables create parent-child dependency pressure without making the schema exotic. It writes CSV artifacts by default because CSV is the most common large local export path and keeps the first benchmark focused.

The benchmark records separate timings for parsing, planning, exporting, validation, total elapsed time, peak memory, artifact size, output directory, validation result, and issues. It also has `--skip-validation` for export-only experiments, but official numbers should keep validation enabled.

### Follow-Up Notes

- Next optimization target: improve export throughput.
- Next reliability target: make validation chunk-aware so it does not need full per-table CSV lists in memory.
- Re-run the benchmark after each meaningful export or validation optimization.
