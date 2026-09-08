# DataBoom Understanding Log

This file is a backend and systems learning notebook for DataBoom. It explains why the engine, API, database, Docker setup, validation path, benchmarks, and reliability decisions exist.

Keep it beginner-friendly, but professional. The goal is to teach how an enterprise-grade synthetic-data platform is designed through real decisions in this repo.

Do not use this file for frontend styling notes, documentation process, copy changes, or routine commit summaries. Add entries only when the change teaches something meaningful about backend architecture, Python implementation, operating-system behavior, database design, Docker/runtime setup, engine performance, latency, reliability, or production tradeoffs.

## Decision: build an engine instead of relying on Faker or ChatGPT alone

### Question

Why does DataBoom need a backend engine instead of just using Faker or asking ChatGPT to generate a large file?

### Answer

Faker can create individual fake values, and an LLM can help explain or plan what data should look like. Neither one is enough to reliably generate large, validated datasets with table order, primary keys, foreign keys, output artifacts, progress tracking, and benchmarkable performance.

DataBoom needs an execution engine. The engine reads structure, plans dependencies, generates rows in a repeatable way, streams files to disk, validates artifacts, and reports operational state.

### Why This Matters

A user may ask for 100k, 500k, or 1M records. At that scale, the problem is no longer "make me a fake name." The real problem is:

- keep relationships valid,
- avoid keeping the entire dataset in memory,
- write files incrementally,
- validate the exact files the user downloads,
- make the run reproducible with a seed,
- measure latency and memory,
- expose progress through the API.

That is backend engineering work. It needs data structures, algorithms, I/O design, and runtime state management.

### Details

Faker is useful inside a generator, but it is a value library. It does not know that `orders.customer_id` must reference an existing `customers.id`, that parent tables must be generated first, or that a CSV file must be validated after export.

ChatGPT is useful for planning and schema interpretation, but it should not directly emit one million records. Large text generation is slow, expensive, hard to validate while streaming, and not naturally aware of relational constraints. The safer architecture is:

1. LLM helps plan intent in later phases.
2. Backend engine turns the plan into deterministic execution.
3. Validator checks output artifacts.
4. API reports run state, progress, timings, and errors.

### Follow-Up Notes

- Faker-style realism can be added behind deterministic strategy interfaces.
- LLM-assisted planning should produce structured plans, not raw output files.
- The benchmark path should always measure real generated artifacts, not prompt output.

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

## Decision: stage relational, document, and graph data support by phase

### Question

Should DataBoom try to support relational databases, NoSQL documents, and graph data all at once?

### Answer

No. The roadmap should keep PostgreSQL relational generation in Phase 1, add NoSQL document data in Phase 2, and add graph data in Phase 3.

### Why This Matters

Each data family has different correctness rules. Relational data depends on tables, primary keys, foreign keys, and dependency ordering. Document data depends on nested shapes, arrays, object identifiers, and optional references. Graph data depends on nodes, edges, labels, properties, and cardinality. Combining all of that too early would make the engine harder to validate and harder for new contributors to understand.

### Details

Relational generation is first because it proves the hardest foundational engine behavior: parse a schema, compute dependency order, preserve references, stream artifacts, and validate the result. Once that is stable, Phase 2 can add NoSQL document generation on top of the same planning, artifact, and validation ideas, but with document-specific contracts. Phase 3 can then add graph data once the planner and operator review experience are strong enough to explain node and edge plans before execution.

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
## Decision: start API generation runs synchronously

### Question

Should the first API generation endpoint introduce background workers, queues, Redis state, and async orchestration immediately?

### Answer

No. The first `/runs` endpoint should execute a local relational generation run synchronously, write artifacts to local disk, and store the run response in the current API process.

### Why This Matters

The existing engine already generates and validates local artifacts. The next backend risk is the HTTP contract: request shape, status response, artifact paths, validation summary, error handling, and client integration. A synchronous endpoint proves that contract without adding queue complexity too early.

### Details

The endpoint accepts PostgreSQL DDL, row counts, seed, domain profile, and output formats. It reuses the same parser, planner, exporter, and validator as the CLI. Artifacts are written under `artifacts/runs/{run_id}` so API runs do not collide with CLI or benchmark outputs.

The in-memory run store is intentionally temporary. It makes `POST /runs`, `GET /runs`, and `GET /runs/{run_id}` useful during local development, but it is not the final production run-state design. Later Phase 2 work can replace it with persistent metadata and background execution without changing the basic response contract.

### Follow-Up Notes

- Add artifact download endpoints before clients need to retrieve generated files.
- Add persistent run state before long-running or multi-worker deployment.
- Add background execution only when progress reporting, cancellation, retries, or large runs require it.

## Decision: expose run artifacts through path-safe API endpoints

### Question

Why add artifact listing and download endpoints before building richer run consumers?

### Answer

The API already creates local artifacts, but a client cannot use them unless it can discover and retrieve files through HTTP. Adding `GET /runs/{run_id}/artifacts` and `GET /runs/{run_id}/artifacts/{relative_path}` closes that loop for local runs without introducing a queue, worker, object storage, or authentication system before those pieces are truly needed.

### Why This Matters

This turns a generation run into a complete API workflow: create a run, read its status, list its outputs, and download the files. That is the minimum contract API clients, CLI automation, and future integrations need before they can offer artifact download buttons or pipeline handoffs.

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
- Add client API-key handling only after the product has a safe local settings pattern.

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

DataBoom works better as the parent platform name because it can hold multiple products without making every feature sound like the same single engine. The code package, CLI command, environment prefix, and Docker defaults now use `databoom`/`DATABOOM`/`DataBoom` consistently.

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

The code still keeps stable package and enum names such as `databoom`, `financial`, and `healthcare`. That is intentional. Whacky product names belong at product boundaries; stable internal names make APIs and tests easier to maintain.

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

## Decision: model product workflows in backend catalog endpoints

### Question

Why add backend product catalog, demo auth, subscriptions, product-run endpoints, and preview endpoints instead of only exposing one generic `/runs` endpoint?

### Answer

The backend needs to model the product workflow explicitly. A generic run endpoint is useful for raw engine testing, but product modules need a stable lifecycle: discover product, subscribe, configure, generate, preview, download, and audit.

### Why This Matters

Product state should not be fake client state. If subscriptions, catalog products, previews, and artifacts are real backend resources, the API contract can evolve toward production without rewriting every client later. It also forces the backend to answer important questions early: which products are runnable, which are planned, what outputs each product supports, and how preview reads are served safely.

### Implementation Detail

The backend owns runnable product definitions in `src/databoom/api/products.py`. Each catalog entry includes schema DDL, default row counts, output formats, a domain profile, features, and plans. The product-run endpoint turns that catalog entry into a normal `GenerationRunRequest`, so it reuses the existing parser, planner, generator, exporter, and validator instead of creating a second generation path.

The table preview endpoint reads the generated CSV artifact for a selected table and returns the first rows as structured JSON. This is better than making clients guess artifact file paths or parse downloaded files by themselves. The backend remains the source of truth for artifact layout.

### Follow-Up Notes

- Replace demo auth with real auth before shared deployment.
- Persist sessions, subscriptions, and run metadata in PostgreSQL instead of app memory.
- Move long-running generation to a job queue before allowing large user-triggered runs.
- Add custom schema upload and saved generation templates once the product run flow is stable.

## Decision: persist API state behind a store boundary

### Question

Why move demo sessions, product subscriptions, and generation-run metadata out of FastAPI app dictionaries?

### Answer

Once a user can log in, subscribe, generate data, preview tables, and download artifacts, that workflow should not disappear whenever the API process restarts. A small persistence layer gives the product a durable backbone while keeping the current route contract stable.

### Why This Matters

In-memory dictionaries are useful for the first proof of concept because they are simple and fast. They are not good enough for a product console. If the API container restarts after a user generates data, the artifact files may still exist on disk, but the API would forget the run ID, product subscription, and session token. That breaks the user's path through the app even though the engine did its work correctly.

PostgreSQL is already part of the DataBoom stack, so storing API metadata there is the natural next step. This improves reliability without introducing a queue, workflow engine, or heavy orchestration system before the project needs one.

### Implementation Detail

The backend now has a `StateStore` protocol. Routes call methods such as `save_session()`, `list_subscriptions()`, and `save_run()` instead of reading and writing raw dictionaries. There are two implementations:

- `MemoryStateStore` keeps tests and fallback local development lightweight.
- `SQLAlchemyStateStore` stores JSON payloads for demo sessions, subscriptions, and generation runs in SQL tables.

This design keeps SQLAlchemy out of route business logic. A route should care about product behavior: authenticate, subscribe, generate, preview, download. It should not know table names or write SQL statements inline. That separation makes the backend easier to change later when the metadata model becomes more normalized.

For the current implementation, run payloads are stored as JSON. That is a practical bridge: the API already has typed Pydantic response models, and storing their JSON form preserves the current contract with minimal code. Later, high-query fields such as run status, product ID, owner, artifact root, duration, row counts, and validation status can be promoted into first-class columns.

### Performance, Reliability, or Maintainability Impact

Reliability improves because Dockerized API runs can survive process restarts while keeping sessions, subscriptions, and run metadata. Maintainability improves because persistence is now a replaceable boundary instead of a pattern duplicated across endpoints.

The performance impact is intentionally small for the current scale. Sessions, subscriptions, and run metadata are tiny compared with generated datasets. The large files still live on local disk under `artifacts/`, so PostgreSQL is not being used as a blob store. That keeps the database focused on metadata and leaves bulk generated data in file artifacts where Phase 1 and Phase 2 can inspect it easily.

### Beginner Explanation

Think of generated CSV/JSON/SQL files as packages in a warehouse. The API metadata is the clipboard that says which packages exist, who requested them, and where to find them. Before this change, the clipboard was wiped whenever the API restarted. Now the clipboard is saved in PostgreSQL.

The `StateStore` is like a service desk window. The rest of the app asks the window for sessions, subscriptions, and runs. Today the window can talk to memory or PostgreSQL. Later it can talk to a more advanced database design without forcing every route to be rewritten.

### Follow-Up Notes

- Replace `metadata.create_all()` with Alembic migrations before production deployment.
- Normalize important run fields into columns when filtering, search, ownership, or run-history queries become more advanced.
- Add real user accounts and authorization before shared deployment.
- Move long-running generation into background jobs before large user-triggered runs become common.
- Add artifact retention and cleanup rules so persisted run metadata cannot point to deleted files without an explicit status.

## Decision: render products by data surface instead of domain product names

### Question

Should DataBoom keep separate product branches such as banking, healthcare, commerce, and similar domain names, or should it keep a smaller catalog organized by the shape of data being generated?

### Answer

Keep four catalog products based on data surface and workflow: Table-Boom for relational data, Docu-Boom for NoSQL document data, Graph-Boom for graph data, and Masker-Boom for masking/redaction. Banking, healthcare, ecommerce, SaaS, and similar names should be demo use cases or domain profiles under those products, not standalone products.

### Why This Matters

Product boundaries should match the engine behavior. Relational tables, JSON documents, graph nodes/edges, and masking policies need different runtime models, previews, validations, and export shapes. Banking versus healthcare usually changes the schema, labels, value generators, or examples, but it does not require a totally separate engine.

This keeps the project easier to scale. A new financial demo can reuse Table-Boom if it is relational. A healthcare document demo can reuse Docu-Boom if it is nested JSON. API clients can choose behavior by reading `product.kind` instead of hard-coding product IDs.

### Details

The backend catalog now exposes a stable `kind` for each product. The API can dispatch relational products to the existing table engine and document products to the Docu-Boom document generator. Planned graph and masking products stay visible in the catalog but return clear planned states until their runtime engines exist.

This is more maintainable than creating a separate backend endpoint family for every domain. If every use case had its own endpoint and generator path, the codebase would quickly contain duplicate artifact logic, duplicate validation states, duplicate run summaries, and duplicated tests.

### Follow-Up Notes

- Table-Boom and Docu-Boom are active for local workflows.
- Graph-Boom should add node/edge models and previews in Phase 3.
- Masker-Boom should add policy, redaction, tokenization, classification, and audit views in Phase 4.
- Phase 2 still needs formal 500k benchmark evidence and deeper structural profiling before production-scale claims are made.

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

## Decision: make CSV validation chunk-aware

### Question

Why change validation if the 500k benchmark already passed?

### Answer

The benchmark passed, but validation still loaded each table's CSV rows into memory before checking row counts, required fields, primary keys, and foreign keys. That was acceptable at 500k, but it is the wrong shape for larger runs. The validator now streams each CSV once and keeps only the key sets needed for integrity checks.

### Why This Matters

For synthetic data generation, validation must scale with the artifact size. Loading full CSV rows into Python dictionaries multiplies memory use because every cell becomes an object. The generated artifact might be only tens of megabytes on disk, while the in-memory representation can be many times larger.

The streaming validator changes the memory profile. On the same 500k benchmark, peak memory dropped from 262.044 MB to 52.811 MB. Validation time also improved from 14.105 seconds to 11.32 seconds. Export still dominates runtime, but validation is now much safer for larger runs.

### Details

The validator now processes one table at a time:

- it checks required values while reading each row,
- it tracks duplicate primary keys for the current table,
- it validates child foreign keys against parent key sets already collected,
- it stores only primary-key sets that future child tables need,
- it discards full row dictionaries immediately.

This works because relational generation already orders tables by dependency. Parent tables are validated before child tables, so parent keys are available when a child row is checked.

### Follow-Up Notes

- Export throughput is now the main 500k bottleneck.
- Future million-record validation may need disk-backed or probabilistic strategies for very large parent key sets.
- Re-run `benchmarks/phase2_500k.py --overwrite` after export optimizations to compare total runtime.

## Decision: make product generation asynchronous and observable

### Question

Why should product generation run asynchronously, and why do we need operation timings instead of only a final success/failure response?

### Answer

Product generation should return a run immediately, then continue in the background. Clients can poll that run to show status, progress, expected time, preview rows, artifact availability, and operation timings.

### Why This Matters

A synchronous API request is fine for tiny demos, but it is a bad user experience for larger generation. The browser waits without useful feedback, reverse proxies can time out, and the user cannot inspect partial output. Synthetic data generation is naturally a long-running job, so the product should treat it as a run lifecycle rather than one blocking HTTP call.

Operation timings also keep performance work honest. If we only know "the run took 50 seconds", we do not know whether parsing, planning, exporting, validation, or file I/O caused the delay. Timings let us optimize the right stage.

### Details

The current implementation uses an in-process `AsyncRunManager`. It creates a run ID, saves a running placeholder, starts generation in a background thread, and lets `GET /runs/{run_id}` return updated progress while the backend is still writing artifacts.

This is the right Phase 2 shape because it gives the product the correct API contract without prematurely adding Celery, Kafka, or a distributed worker platform. Those tools are useful when we need retries, distributed workers, durable queues, priority scheduling, or event streaming. For the local product, a small background manager is simpler and easier to reason about.

Progress is now based on row counters emitted by the generation pipeline. Table-Boom's artifact exporter reports generated rows by table. Docu-Boom reports generated documents by collection. The async manager turns those callbacks into generated-row counts, current resource, rows per second, remaining seconds, and progress percentage.

This is better than a timer-only progress bar. A timer can guess that a job is halfway done because half of the expected time has passed, but that can be wrong when a table is unusually wide, the disk is slow, or validation takes longer than normal. Row counters are grounded in actual work completed. The ETA still exists, but it is now supported by observed throughput.

The API now reports:

- run status: running, completed, or failed,
- generated rows,
- current table or collection,
- progress percentage,
- rows per second,
- expected seconds,
- remaining seconds,
- operation timings,
- generated resource metadata,
- validation summary when complete.

The exporter flushes early preview rows to disk. That lets preview endpoints read the first rows while a large relational run is still active. Docu-Boom also streams JSON and NDJSON artifacts, and the preview endpoint can read partially flushed NDJSON lines before the final JSON array is complete.

### Follow-Up Notes

- The local async manager is not a production queue.
- A later production worker should preserve the same run response contract.
- Future production progress can add per-stage validation progress and persisted running-job heartbeats.
- Add structured logs with run IDs before production deployment.

## Decision: explain how DataBoom generates synthetic data

### Question

Does DataBoom generate data from thin air? Is it random? Is ChatGPT creating every row?

### Answer

DataBoom does not create useful data from nothing, and ChatGPT is not writing every row. The engine creates deterministic synthetic data from inputs: schema definitions, document specs, row counts, domain profiles, constraints, output formats, and a seed. The generated values use controlled pseudo-randomness plus rules, templates, and relationship tracking.

### Why This Matters

This distinction is the whole reason an engine is needed. A one-off prompt can produce a small sample, but it cannot reliably produce hundreds of thousands of rows with primary keys, foreign keys, output files, validation reports, repeatable seeds, and predictable performance.

DataBoom acts like a factory. The schema/spec is the blueprint. The seed is the machine setting. The generator is the assembly line. The validator is quality control.

### Details

For Table-Boom relational generation, the flow is:

1. Parse the PostgreSQL DDL into normalized schema models.
2. Validate that tables, columns, primary keys, foreign keys, and constraints make structural sense.
3. Build a relationship graph so parent tables are generated before child tables.
4. Build a generation plan with row counts, column strategies, domain profile, output formats, and seed.
5. Create deterministic random streams from the seed.
6. Generate rows table by table.
7. Register generated parent keys so child rows can reference real parent rows.
8. Stream CSV, JSON, and SQL artifacts to local disk.
9. Validate required fields, row counts, primary keys, and foreign keys.

For Docu-Boom document generation, the flow is similar but uses collection specs instead of SQL DDL. A collection spec declares fields, nested objects, arrays, object IDs, and references. The generator uses those specs to write JSON and NDJSON documents.

The "random" part is controlled pseudo-randomness. That means the values look varied, but the same seed and same input plan produce the same output again. This is important for debugging, demos, tests, and repeatable benchmarks.

Examples:

- A primary key can be generated as a stable sequence.
- A foreign key is chosen from parent keys that were already generated.
- A status field is chosen from a controlled list such as `active`, `pending`, or `blocked`.
- A timestamp is produced from a base date plus a seeded offset.
- A money value is produced from a seeded numeric range.
- An email can be created from a deterministic template.
- A document object ID comes from a stable seed-derived hexadecimal value.

So the data is not production data, and it is not copied from a sensitive database. It is synthetic data shaped by the schema, rules, and seed. Later privacy phases can add masking and profiling, but the current generator already avoids the fragile pattern of asking an LLM to directly emit giant files.

### Follow-Up Notes

- Phase 3 can use an LLM to help plan generation intent, but the deterministic engine should still execute the plan.
- Phase 4 Masker-Boom should add privacy policies for real sensitive source data.
- More domain profiles can improve realism without changing the core engine contract.

## Decision: add cooperative cancel and retry for async product runs

### Question

Why add cancel and retry controls to async runs before adding Celery, Kafka, or a distributed worker system?

### Answer

The API already has long-running run state. Once a run can be `running`, users and operators need basic control actions:

- cancel a run that is no longer wanted,
- retry a run that failed because of a transient bug, bad input, or runtime interruption,
- preserve enough context to know what was retried.

Phase 2 can support those controls inside the current in-process async manager. Celery, Kafka, or a distributed worker can come later when we need durable queues, multi-process workers, priority scheduling, or cross-machine execution.

### Why This Matters

Long-running data generation is not like a normal CRUD request. A normal request either returns quickly or fails quickly. A generation run may write many files over many seconds or minutes. Without cancel/retry, the API can start work but cannot operate it.

This is a reliability feature more than a latency optimization. It does not make a successful 500k run faster by itself. It reduces wasted runtime when a run should stop, and it gives failed runs a clean recovery path without requiring the user to rebuild the whole request manually.

### OS and Python Detail

Python threads cannot be safely killed from the outside. A thread may be holding a file handle, writing a CSV row, updating shared state, or executing cleanup code. Force-killing it could leave partial files, locked resources, or corrupted process state.

The safer pattern is cooperative cancellation:

1. The API marks a run as canceled.
2. The async manager sets a cancellation event for that run.
3. The generation pipeline checks that event at progress checkpoints.
4. When cancellation is noticed, the worker raises an internal cancellation signal.
5. The manager records a final `canceled` run state with elapsed time and partial progress.

This is why the implementation uses a `threading.Event` instead of trying to terminate a thread.

### Implementation Detail

The async manager now stores:

- a `Future` for the submitted background task,
- a cancellation `Event`,
- the original product-run context,
- latest generated-row progress,
- the latest run response.

`POST /runs/{run_id}/cancel` marks a running run as `canceled`. If the task has not started yet, `Future.cancel()` may prevent it from running at all. If it is already running, the cancellation event stops it at the next progress callback.

`POST /runs/{run_id}/retry` starts a fresh async run from the original product and payload. The new run records `retry_of_run_id`, so the retry lineage is visible in the API response.

Failed runs now return clearer error strings such as `RuntimeError: forced generation failure` instead of only the raw message. That helps beginners and operators see whether the failure came from validation, a value error, an unexpected runtime error, or another exception type.

### Tradeoffs

This is not yet a production distributed job system:

- cancellation is cooperative, not instant,
- retry context is in the current API process,
- a process restart can preserve saved run state but not in-memory retry context,
- queued/running work still belongs to one local process.

That is acceptable for Phase 2 because it keeps the API contract correct without adding heavy infrastructure too early.

### Follow-Up Notes

- Move retry context into persisted run metadata before multi-process deployment.
- Add durable queues when jobs need to survive API process restarts while running.
- Add per-stage cancellation checks if validation and future profiling stages become long-running.
- Add cleanup policy for canceled partial artifacts so local disk does not grow forever.

## Decision: move workspace sources into the backend contract

### Question

Why should database/workspace choices live in the backend instead of staying as a frontend dropdown?

### Answer

The backend must own workspace sources because a source is not only a UI label. It defines the data surface the engine should understand:

- which product can use it,
- whether it is relational, document, graph, or masking data,
- which database or source engine it represents,
- which tables, collections, nodes, or policy resources exist,
- how many rows/documents are expected,
- which columns or fields shape generation.

If this information stays hardcoded in the frontend, the UI can show a database called "Core Banking Sandbox", but the backend still has no idea what that means. The result is a fake dropdown: users select one thing while the generator runs another thing.

### What Changed

The API now exposes workspace sources as a backend-owned contract:

- `GET /workspace-sources`
- `GET /workspace-sources/{source_id}`
- `GET /products/{product_id}/workspace-sources`

Each source returns product compatibility, source kind, engine, host, status, and resources. A resource is a table, collection, node set, edge set, or masking sample with an estimated row count and field/column metadata.

Product runs now accept `source_id`. The backend validates that the source belongs to the selected product and kind. For example, a Docu-Boom MongoDB source cannot be used with a Table-Boom relational run.

### Why This Is Better

This makes the dashboard and engine agree on one source of truth. The frontend asks the backend which databases exist. The user selects one. The backend receives that `source_id` when generation starts.

For Table-Boom, the engine can synthesize a small PostgreSQL DDL from source resources and generate source-specific tables. For Docu-Boom, it can synthesize document collection specs from source resources and generate source-specific collections.

That means the selected source affects actual artifacts, not only the visible menu.

### Beginner-Friendly Example

Before this change:

1. Frontend shows "Core Banking Sandbox".
2. User selects it.
3. Backend still generates the default commerce tables.
4. UI and backend are out of sync.

After this change:

1. Backend exposes "Core Banking Sandbox" with `customers`, `bank_accounts`, and `transactions`.
2. Frontend renders those resources.
3. User starts a run with `source_id = core-banking`.
4. Backend validates source/product compatibility.
5. Backend generates `customers`, `bank_accounts`, and `transactions` artifacts.

### Performance and Scaling Notes

This change is not primarily a latency optimization. It is a correctness and extensibility improvement. The important performance benefit comes later: once source metadata is backend-owned, we can cache introspection results from real databases instead of rediscovering schemas on every page load or generation request.

Future production path:

1. Store workspace sources in Postgres instead of the demo catalog.
2. Store encrypted connection references or secret IDs, not raw secrets.
3. Add source introspection jobs for PostgreSQL, MongoDB, and later graph stores.
4. Cache discovered schema metadata with version hashes.
5. Reuse cached source metadata to build generation plans quickly.

This keeps the architecture clean: the frontend renders workspace state, while the backend owns data-source truth and generation planning.

## Decision: persist workspace sources and refresh them from PostgreSQL introspection

### Question

Why was the next backend step to persist workspace sources instead of only adding another hardcoded demo database?

### Answer

A hardcoded source list is useful for proving the UI shape, but it cannot support real users. Different teams will have different databases, different table names, different schemas, and different row expectations. If DataBoom wants to behave like a product workspace, source metadata has to be state, not code.

The backend now treats workspace sources as stored API state:

- test/local memory state starts with the built-in demo sources,
- SQL-backed Docker state seeds the same demo sources into `databoom_workspace_sources`,
- new sources can be created through `POST /workspace-sources`,
- source metadata can be refreshed and saved after live PostgreSQL introspection,
- product runs receive a resolved `WorkspaceSource` object instead of looking only at the old static catalog.

This is important because the dashboard can now show the same source resources that the generator will use. If a refreshed source contains `invoices` and `invoice_lines`, a Table-Boom run with that `source_id` generates those tables instead of falling back to the old default commerce tables.

### Question

Why does refresh store table metadata instead of introspecting the database every time the page loads or a run starts?

### Answer

Database introspection is an external operation. It may need a network connection, credentials, connection pooling, permissions, timeout handling, and later secret management. Running it on every dashboard page load would make the UI slower and less reliable. Running it on every generation request would also make generation latency depend on the source database even when the schema has not changed.

The better production pattern is:

1. Refresh or connect a source explicitly.
2. Convert live database metadata into DataBoom's normalized resource contract.
3. Persist that resource contract.
4. Let the dashboard and generator reuse the saved metadata.

This separates "discover the source shape" from "generate data from the known shape." That separation is the beginning of schema caching.

### Question

What changed in the async engine path?

### Answer

Async runs now carry the resolved workspace source inside the run context. That matters for two reasons.

First, the running placeholder can show the correct planned tables or collections before generation finishes. Without this, a user could select a refreshed source but see old default tables during the run.

Second, retries must use the same source metadata as the original run. If the retry only kept the product and payload, it could accidentally resolve a different source later if the source catalog changed. Carrying the resolved source keeps the retry behavior stable for the current local-process implementation.

### Performance and Scaling Notes

This change is mostly correctness and architecture, not raw speed. It does, however, remove a future latency trap:

- Without persisted source metadata, every dashboard load or run might need live database introspection.
- With persisted source metadata, the UI and generator can reuse cached table/column data immediately.

The next optimization step is to attach a schema version hash or refresh timestamp to each source. Then DataBoom can skip unnecessary introspection, show when metadata is stale, and refresh only when the operator asks or when a background job detects schema drift.

## Decision: store refreshed schema metadata as both resource details and a DDL snapshot

### Question

Why not store only table names and column names after PostgreSQL refresh?

### Answer

Table and column names are enough for navigation, but they are not enough for relational data generation. A real relational generator needs to know which columns are primary keys, which columns are foreign keys, which table is the parent, which columns are nullable, and what each column's database type is.

Without that metadata, a source refresh can make the UI look correct while the generator still behaves like a flat-table generator. For example, `invoice_lines.invoice_id` would be just another integer column instead of a child key that must point to `invoices.id`.

### What Changed

Workspace resources now keep richer schema metadata:

- `schema_name`
- `primary_key`
- `foreign_keys`
- `unique_constraints`
- `column_details`
- `schema_ddl` on the workspace source
- `refreshed_at` on the workspace source

The `columns` list still exists because it is convenient for frontend navigation, but it is no longer the only schema representation.

### Why Store a DDL Snapshot?

The existing Table-Boom planner already understands PostgreSQL DDL. Instead of inventing a separate generation path for refreshed sources, the refresh step converts normalized introspection metadata back into PostgreSQL `CREATE TABLE` DDL.

That gives us a clean bridge:

1. PostgreSQL introspection reads the live database.
2. DataBoom normalizes it into `DatabaseSchema`.
3. Workspace refresh stores resource metadata for the UI.
4. Workspace refresh stores a DDL snapshot for the generator.
5. Product runs parse that DDL snapshot and reuse the existing relationship-aware planner.

This avoids duplicate planner logic and keeps the engine modular.

### Beginner-Friendly Example

If PostgreSQL introspection finds:

- `billing.invoices(id primary key)`
- `billing.invoice_lines(invoice_id references billing.invoices(id))`

DataBoom now stores that relationship and generates from it. During generation, `invoice_lines.invoice_id` is selected from generated `invoices.id` values, so child rows point to real parent rows.

### Performance Note

This is not a micro-optimization. It is a planning-quality improvement. The performance benefit is that future runs can use the saved DDL snapshot immediately instead of introspecting the source database again. That reduces repeated connection overhead and makes generation less dependent on source database availability after refresh.

## Decision: keep source profiling optional and separate from schema refresh

### Question

Why is profiling a separate endpoint instead of being bundled into every schema refresh?

### Answer

Schema refresh and data profiling answer different questions.

Schema refresh asks: "What is the shape of this database?" It needs table names, column names, types, primary keys, foreign keys, and constraints.

Profiling asks: "What does the data distribution look like?" It may need row counts, null counts, distinct counts, min/max values, and common values. Those queries can be much heavier than schema introspection because they scan actual table data.

Bundling profiling into every refresh would make a simple metadata refresh slow and risky on large customer databases. Keeping profiling optional lets the operator decide when the extra accuracy is worth the extra database work.

### What Changed

DataBoom now has a profiling boundary under `databoom.profiling` and an API route:

- `POST /workspace-sources/{source_id}/profile`

The PostgreSQL profiler reports:

- table row counts,
- per-column null counts,
- null rates,
- distinct counts,
- min and max values,
- top observed values.

### Why This Improves Output Quality

Random-looking synthetic data is easy. Useful synthetic data needs shape. If a status column is usually `active`, sometimes `paused`, and rarely `blocked`, the generator should eventually learn that distribution. If a column is 70% null, generated data should reflect that. If amounts usually sit in a narrow range, generated values should not be wildly unrealistic.

This profiling endpoint does not yet feed those statistics into generation automatically. It creates the backend contract needed for that next step: profile first, store profile hints, then use those hints during planning and value generation.

### Performance Note

Profiling uses aggregate SQL and can be expensive on large tables. In production, this should become a background job with:

- sampling controls,
- timeouts,
- per-table limits,
- cached profile snapshots,
- clear freshness timestamps.

For Phase 2, exposing profiling as an explicit endpoint is the right balance. It proves the contract without forcing every source refresh or generation run to scan source data.

## Decision: make foreign-key selection an explicit generation strategy

### Question

Why did we add a `ForeignKeySelectionStrategy` instead of keeping foreign-key choice hidden inside the row generator?

### Answer

Foreign keys are not ordinary values. A generated email, amount, or status can be chosen independently for each row. A foreign key cannot. It must point to a generated parent key, and the way child rows choose parent rows changes the shape of the entire dataset.

Before this change, DataBoom used deterministic random selection for foreign keys. That preserved referential integrity, but it could accidentally create poor fanout. For example, if 9 generated users reference 3 generated accounts, random selection might give one account 6 users, another 3 users, and another 0 users. The output is technically valid, but the relationship distribution is noisy and less useful for demos, tests, and downstream joins.

The engine now makes that policy explicit through `ForeignKeySelectionStrategy`:

- `balanced_fanout`
- `random`

The default is `balanced_fanout`.

### How Balanced Fanout Works

For each child-to-parent relationship, DataBoom computes:

- a deterministic offset,
- a deterministic stride that is coprime with the number of parent keys.

Then each child row chooses:

```text
parent_index = (offset + row_index * stride) % parent_count
```

Because the stride is coprime with the parent count, the generator cycles through every parent key before repeating. This gives stable spread without storing a shuffled list of every parent key.

### Beginner-Friendly Example

Suppose DataBoom generates:

- 3 accounts,
- 9 users,
- `users.account_id` references `accounts.id`.

With balanced fanout, each account receives exactly 3 users. With random fanout, the output is still deterministic for a seed, but the distribution can be uneven.

### Why Keep Random Fanout?

Balanced fanout is a better default for stable local demos and test fixtures. Random fanout is still useful when a user wants simulation-style variation. Keeping both strategies makes the engine more flexible without adding complexity to the row loop.

### Performance Note

Balanced fanout is O(1) per child row. The registry stores one `(offset, stride)` pair per relationship. It does not sort parent keys, build a huge repeated key list, or shuffle all child assignments.

This is mainly a quality optimization, but it also protects future performance: relationship behavior can now evolve behind a strategy boundary. The next steps are to add fanout quality metrics, profile source relationship distributions, and eventually choose child keys from observed fanout profiles.

## Decision: report relationship fanout metrics during validation

### Question

Why add relationship fanout metrics to the validation report if validation already checks foreign keys?

### Answer

Foreign-key validation answers a yes/no question: "Does every child key point to an existing parent key?"

That is necessary, but it is not enough. A dataset can pass foreign-key validation while still having poor relationship shape. For example:

- 100 customers exist,
- 1,000 orders exist,
- every order references a valid customer,
- but 90 customers receive zero orders.

The database is valid, yet the synthetic data is not very useful for testing customer-order workflows. Fanout metrics make this visible.

### What Changed

`ValidationReport` now includes `relationship_metrics`. Each metric describes one generated foreign-key relationship:

- child table and child columns,
- parent table and parent columns,
- number of parent keys,
- number of child rows,
- minimum children per parent,
- maximum children per parent,
- average children per parent,
- number of empty parents.

The API validation summary also exposes these metrics, so the dashboard and future quality reports can use the same backend contract.

### Beginner-Friendly Example

If DataBoom generates:

- 2 accounts,
- 3 users,
- `users.account_id` references `accounts.id`,

the relationship metric can report:

- `parent_key_count = 2`
- `child_row_count = 3`
- `min_children_per_parent = 1`
- `max_children_per_parent = 2`
- `average_children_per_parent = 1.5`
- `empty_parent_count = 0`

This tells us that every account received at least one user.

### Why This Helps Performance Work

Optimization should not only make generation faster. It should protect useful output quality while speed improves. Fanout metrics give us a measurable guardrail when we change relationship strategies, parent-key storage, batching, or profile-driven generation.

In the next stages, source profiling can record observed fanout distributions from real schemas, and quality reports can compare generated fanout against those source profiles.

## Decision: add source relationship profiling before profile-driven fanout

### Question

Why profile source relationship fanout if generated validation already reports fanout?

### Answer

Generated fanout metrics describe DataBoom's output. Source relationship profiling describes the input database shape. We need both before we can make profile-driven generation credible.

Generated metrics answer:

"What did DataBoom produce?"

Source relationship profiling answers:

"What does the source relationship distribution look like?"

Once both exist, a future quality report can compare them.

### What Changed

The source profiler now reports `RelationshipProfile` entries for live PostgreSQL sources. For each foreign-key relationship, the profiler captures:

- child table and child columns,
- parent table and parent columns,
- number of parent keys,
- number of non-null child rows,
- number of distinct parent keys referenced by children,
- minimum children per parent,
- maximum children per parent,
- average children per parent,
- number of parent keys with no child rows.

The workspace source profile API exposes these relationship profiles alongside table and column profiles.

### Why This Is Not Yet Full Profile-Driven Generation

This change only measures source fanout. It does not yet make the generator reproduce that fanout. That separation is intentional.

The correct sequence is:

1. Measure generated fanout.
2. Measure source fanout.
3. Persist source fanout snapshots.
4. Compare generated fanout to source fanout.
5. Add a profile-driven relationship strategy.

Skipping straight to step 5 would make the generator harder to debug because we would not have the measurement layer needed to prove improvement.

### Performance Note

Relationship profiling groups child rows by foreign-key columns. That can be expensive on very large source tables. In production, this should support sampling, limits, and cached snapshots. For now, the profile endpoint is explicit, so operators choose when to run that heavier scan.

## Decision: persist latest source profile snapshots

### Question

Why store source profiles instead of profiling the database every time generation runs?

### Answer

Profiling a source database is measurement work. Generation is production work. If we mix the two on every run, generation latency becomes dependent on the size and load of the source database.

For example, column profiling may run `COUNT`, `COUNT DISTINCT`, `MIN`, `MAX`, and top-value grouping queries. Relationship profiling may group child rows by foreign-key values. These operations are useful, but they are not free. On a small demo database they finish quickly. On a real customer database with millions of rows, they can take seconds or minutes depending on indexing, table size, network latency, and database load.

By persisting the latest profile snapshot, DataBoom gets a clean workflow:

1. Refresh schema when table structure changes.
2. Profile source data when an operator wants updated statistics.
3. Store the profile snapshot with `generated_at`.
4. Let generation and quality checks read the stored snapshot.

That means a generation run can use known source hints without scanning the live source every time.

### What Changed

DataBoom now stores the latest source profile per workspace source in the API state store.

In memory-backed mode, the profile snapshot is kept in process. In SQL-backed mode, it is stored as JSON in the state database. The snapshot includes:

- table row counts,
- column null rates,
- distinct counts,
- min and max values,
- top values,
- relationship fanout statistics.

The profile endpoint now saves the snapshot after a successful source scan, and a read endpoint returns the latest stored profile.

### Why This Improves Architecture

This introduces a clear boundary:

- `profiling` knows how to measure source data and serialize profile snapshots,
- `state` knows how to persist and retrieve the latest snapshot,
- `routes` only coordinates the HTTP flow,
- future `generation` and `quality` modules can consume profile hints without knowing where they were stored.

That separation matters because profile-driven generation should not depend on a live database connection. A generated dataset should be reproducible from a schema, seed, row counts, and a profile snapshot.

### Performance Impact

The main latency improvement is avoiding repeated source scans. If source profiling takes 5 seconds and generation takes 1 second, running both every time makes each generation feel like a 6 second job. With a cached profile, repeated generation can stay close to the 1 second path until the profile needs refreshing.

The exact numbers will depend on the source database and dataset size, so the next benchmark work should measure:

- profile scan time,
- cached generation time,
- uncached generation plus profiling time,
- how snapshot size grows with table and column count.

### Why Only The Latest Snapshot For Now?

A profile history table would be useful later for drift analysis. But for the current engine optimization path, the planner only needs one current profile to generate better hints. Keeping the first version as "latest snapshot per source" gives us the value without adding retention policy, cleanup jobs, or UI complexity before they are needed.

## Decision: compress sequential parent keys in the foreign-key registry

### Question

Why optimize the foreign-key registry if generation was already correct?

### Answer

Correctness and scale are different problems.

The generator must remember parent primary keys so child rows can reference valid parents. For example, accounts must be generated before transactions, and every transaction needs an existing `account_id`.

The first implementation stored every parent key as a tuple in a Python list:

```text
[(1,), (2,), (3,), ...]
```

That works, but for the most common relational schema pattern, it wastes memory. Most tables use a single integer primary key where generated IDs are simply:

```text
1, 2, 3, 4, 5, ...
```

For one million parent rows, storing one million Python tuples is far heavier than remembering:

```text
sequential_count = 1_000_000
```

The child selector can still retrieve key number `314` by returning `(315,)`, because row indexes are zero-based and generated IDs are one-based.

### What Changed

DataBoom now uses a `ParentKeyStore` inside the foreign-key registry.

For sequential single-column integer keys, it stores only a count. No tuple list is materialized.

If the key shape stops matching that simple pattern, the store falls back to regular materialized storage. That protects cases like:

- composite primary keys,
- UUID primary keys,
- string primary keys,
- imported or future non-sequential key strategies.

### Why This Is Safe

The optimization does not change the public row output. It only changes how parent keys are stored internally.

Balanced fanout and random fanout still ask the registry for "the key at index N". The registry decides whether that key comes from:

- a compressed sequential range, or
- a materialized tuple list.

That means generation behavior stays deterministic while memory usage improves for the common case.

### Performance Impact

The biggest gain is memory pressure, not CPU.

Before this change, one million generated parent IDs meant one million tuple objects plus one million integer references in a list. After this change, the registry can represent that same parent-key set with a single integer count.

Lower memory pressure helps large runs because Python spends less time allocating objects, keeping them alive, and eventually cleaning them up. It also leaves more memory available for export buffers, validation, and API responses.

### Tradeoff

The fallback path must materialize previously compressed keys if a sequence breaks. That is acceptable because sequence breaks should be rare for generated numeric primary keys. If a future generator deliberately produces non-sequential parent IDs, correctness matters more than compression, so materializing the keys is the right behavior.

## Decision: add a one-million-row relational benchmark harness

### Question

Why add another benchmark if 100k and 500k benchmarks already exist?

### Answer

The 100k and 500k benchmarks prove early scale, but they do not fully answer whether the engine shape is ready for million-row workloads. One million rows is where memory pressure, artifact size, validation time, and relationship storage choices become harder to hand-wave.

A benchmark is not just a demo. It is a repeatable contract that says:

- this schema shape was tested,
- these row counts were tested,
- these output formats were tested,
- parse, plan, export, validation, memory, and artifact-size timings were recorded.

Without that contract, performance discussions become vague.

### What Changed

DataBoom now has a `benchmarks/relational_1m.py` script for a five-table relational workload:

- `customers`,
- `products`,
- `orders`,
- `order_items`,
- `payments`.

The default row counts add up to exactly 1,000,000 records. The relationships exercise parent-child selection across multiple paths: orders reference customers, order items reference orders and products, and payments reference orders.

### Why Include `--scale`?

The script supports `--scale` for smoke tests. A smoke run checks that the benchmark code path works without generating the full million rows.

The official benchmark should use:

```bash
.venv/bin/python benchmarks/relational_1m.py --overwrite
```

A quick local smoke check can use:

```bash
.venv/bin/python benchmarks/relational_1m.py --scale 0.001 --overwrite
```

This distinction matters. Smoke tests prove the script works. Full-scale runs produce benchmark numbers.

### Why This Helps Optimization

Future changes can now compare against the same one-million-row workload. That gives us a clean way to evaluate improvements like:

- parent-key compression,
- chunked export,
- larger CSV buffers,
- profile-driven fanout,
- validation streaming,
- future direct database loading.

The benchmark does not automatically make the engine faster. It makes speed measurable, which is the first requirement for serious optimization.

### Smoke Result From This Commit

I ran the benchmark at `--scale 0.001`, which generated 1,000 records across the same five-table shape.

Result from this environment:

- total time: 0.365 seconds,
- export time: 0.317 seconds,
- validation time: 0.027 seconds,
- peak memory: 0.778 MB,
- artifact size: 0.041 MB,
- validation passed.

This is not the official 1M benchmark number. It proves the benchmark path works quickly after implementation.

## Decision: use source profile histograms for relationship fanout

### Question

Why did we need child-count histograms instead of only min, max, and average fanout?

### Answer

Minimum, maximum, and average are useful summaries, but they do not describe the shape of a relationship.

Imagine two source databases:

```text
Source A: [2, 2, 2, 2, 2]
Source B: [0, 0, 0, 0, 10]
```

Both have the same average: 2 children per parent.

But they mean very different things:

- Source A is evenly distributed.
- Source B has many empty parents and one heavy parent.

If DataBoom only uses the average, it will make both relationships look balanced. That is wrong for source B. Real datasets often have skew: inactive customers, accounts with no transactions, products with no orders, or one customer with many events.

The profile now stores child-count frequencies, for example:

```text
0 children -> 2 parents
1 child    -> 2 parents
4 children -> 1 parent
```

That gives the generator enough shape information to create sparse and heavy parent relationships.

### What Changed

The generation plan now supports `ForeignKeySelectionStrategy.PROFILE_DRIVEN`.

Each foreign-key source can carry a `RelationshipFanoutHint`, which contains:

- child table,
- child columns,
- parent table,
- parent columns,
- child-count frequency buckets.

The PostgreSQL profiler now records these buckets from live source data. The API stores them in source profile snapshots. When a product run selects a workspace source that already has a cached profile, Table-Boom converts the profile into relationship hints and uses profile-driven fanout.

If there is no profile hint for a relationship, the generator falls back to balanced fanout.

### How The Algorithm Works

For each relationship:

1. Read the source child-count frequency buckets.
2. Scale those buckets to the number of generated parent rows.
3. Scale the resulting per-parent child counts to the requested generated child row count.
4. Build a deterministic parent assignment sequence.
5. Use the assignment sequence while generating child rows.

The algorithm is deterministic because it uses the run seed. The same schema, row counts, profile hint, and seed produce the same output.

### Example

Suppose the source profile says:

```text
0 children -> 2 parents
1 child    -> 2 parents
4 children -> 1 parent
```

For 5 generated parents and 10 generated children, DataBoom can produce a fanout shape like:

```text
[0, 0, 2, 2, 6]
```

That keeps the important pattern:

- some parents remain empty,
- some parents get a small number of children,
- one parent is much heavier.

Balanced fanout would produce something like:

```text
[2, 2, 2, 2, 2]
```

That is valid, but less source-shaped.

### Why This Improves Quality

Profile-driven fanout makes generated data better for testing real systems. Many application bugs appear only when data is uneven:

- dashboards with empty accounts,
- pagination with heavy customers,
- reconciliation jobs with high-volume transactions,
- joins where many parent rows have no children,
- performance tests where relationship skew matters.

This is a major step from "referentially valid synthetic data" toward "source-shaped synthetic data".

### Performance Tradeoff

Profile-driven fanout builds a parent-index assignment for the generated child rows in that relationship. That costs some memory proportional to child-row count. For the current local MVP, this is acceptable and keeps the algorithm simple and debuggable.

The balanced strategy remains the lower-memory default when no profile hint is available. A later optimization can store profile assignments as run-length ranges instead of a full parent-index sequence if very large profiled relationships need lower memory.

## Decision: add a one-million-row composite-key benchmark harness

### Question

Why do we need a separate composite-key benchmark after the normal one-million-row benchmark?

### Answer

Single-column integer primary keys are the easiest relational path. DataBoom can compress keys like:

```text
1, 2, 3, 4, ...
```

Composite keys are harder because a parent identity is a tuple:

```text
(tenant_id, account_id)
```

The engine must remember and replay both values together. A child row is valid only when every referenced column matches the same parent tuple.

For example, this is valid:

```text
tenant_id = 17
account_id = 17
```

if the parent key `(17, 17)` exists.

This is not valid:

```text
tenant_id = 17
account_id = 42
```

unless the parent key `(17, 42)` exists.

That means composite foreign keys test a different part of the engine than simple IDs. They exercise tuple storage, tuple selection, CSV validation, and relationship metrics for multi-column keys.

### What Changed

DataBoom now has `benchmarks/composite_keys_1m.py`.

The benchmark uses five related tables:

- `customer_accounts` with composite primary key `(tenant_id, account_id)`,
- `orders` with composite foreign key `(tenant_id, account_id)`,
- `order_items` referencing orders,
- `shipments` referencing orders,
- `payments` with composite foreign key `(tenant_id, account_id)`.

The default row counts add up to exactly 1,000,000 records.

### Why This Completes Track A

Track A is about relational engine speed and relationship quality. Before this benchmark, DataBoom had strong coverage for simple-key relationships. The composite benchmark closes the remaining proof gap:

- simple parent-child relationships,
- large five-table relationships,
- profile-driven fanout,
- sequential key compression,
- composite primary and foreign-key validation.

This does not mean every possible relational schema is solved. It means the Phase A benchmark surface now covers both common simple-key schemas and harder tuple-key schemas.

### Smoke Result From This Commit

I ran the benchmark at `--scale 0.001`, which generated 1,000 records across the same five-table composite-key shape.

Result from this environment:

- total time: 0.645 seconds,
- export time: 0.541 seconds,
- validation time: 0.045 seconds,
- peak memory: 0.814 MB,
- artifact size: 0.057 MB,
- validation passed.

This is not the official 1M benchmark number. It proves the composite benchmark path works quickly after implementation.

## Decision: add column profile hints to the generation plan

### Question

Why add `ColumnProfileHint` before changing the value generator?

### Answer

Profile-driven generation needs a stable contract between source profiling and value generation.

The source profiler observes facts like:

- how many rows were sampled,
- how often a column is null,
- how many distinct values exist,
- the minimum and maximum values,
- the most common values.

The value generator should not read raw profiler objects directly. If it did, generation would become tightly coupled to PostgreSQL profiling. Later, when DataBoom supports other sources, every source would need to mimic PostgreSQL internals.

`ColumnProfileHint` solves that by converting source profiles into a generation-friendly contract.

### What Changed

The generation plan can now carry column hints. Each column plan can optionally hold:

- `sample_count`,
- `null_rate`,
- `distinct_count`,
- `min_value`,
- `max_value`,
- `top_values`.

Product runs now convert cached source profile snapshots into these hints and attach them while building the plan.

### Why This Is Good Architecture

This separates responsibilities:

- profiling measures the source,
- planning decides which hints belong to which columns,
- value generation consumes hints without knowing where they came from.

That gives us a clean path for multiple source systems later. PostgreSQL, document stores, uploaded CSVs, and future graph sources can all produce the same hint contract.

### Why It Does Not Change Output Yet

This step only carries hints through the system. It does not yet use them to generate values.

That is intentional. First we prove the data reaches the plan correctly. Then we add behavior one category at a time:

1. categorical weighted sampling,
2. numeric ranges,
3. datetime ranges,
4. string patterns,
5. quality reports comparing generated output back to source hints.

Doing it in this order makes bugs easier to isolate. If generated values look wrong later, we can tell whether the issue is in profiling, planning, or value generation.

## Decision: use profile top values before generic value providers

### Question

How does DataBoom generate data from thin air without just making random junk?

### Answer

The engine does not ask a prompt to invent every row. It builds a generation plan, then each row is produced from deterministic rules:

- schema rules decide which columns are primary keys, foreign keys, defaults, or generated values,
- relationship strategies decide which parent rows child rows should reference,
- profile hints describe what the source data looked like,
- value providers fill in useful fallbacks when no profile exists,
- seeded random streams make the output repeatable.

That means generated data is random only in a controlled sense. The engine uses randomness as a deterministic sampling tool, not as the architecture.

### Question

Why should top values from a source profile run before the generic domain provider?

### Answer

If a source profile says a `status` column is usually `active` and sometimes `inactive`, the generator should respect that before guessing values like `pending`, `posted`, or `disabled`.

This matters because domain providers are broad assumptions. Source profiles are evidence from the actual database or dataset shape. Evidence should win over assumptions.

The new flow is:

1. reject invalid requests such as foreign-key value generation in the value provider,
2. apply source null rate for nullable columns,
3. preserve primary-key strategy,
4. sample categorical top values from the profile when available,
5. fall back to domain-specific or generic generated values.

### Question

How does weighted top-value sampling work?

### Answer

Each top value has a count from the source profile. If the source profile says:

- `active`: 80,
- `inactive`: 20,

then the generator treats the column like an 80/20 weighted choice.

Because it uses the seed manager, the result is repeatable. The same seed, table, column, and row index produce the same value every time.

When the top values do not cover the entire known distribution, the generator estimates coverage from:

- sample count,
- null rate,
- total top-value count,
- distinct count.

If the top values cover only part of the source distribution, some rows intentionally fall back to normal providers. This avoids collapsing a high-cardinality column into only the few values that appeared in the top-value list.

### Question

How does this improve quality?

### Answer

Before this change, a categorical source column could be generated from naming heuristics alone. A `status` column might look plausible, but it was not shaped by the observed source.

After this change, profiled categorical columns can preserve:

- common category names,
- relative category frequency,
- source null rate,
- deterministic repeatability.

This is an important step toward quality reporting. Once generated output is influenced by source profiles, DataBoom can compare generated distributions against those source profiles and explain how close the output is.

## Decision: generate numeric values inside profiled source ranges

### Question

Why use source `min_value` and `max_value` for numeric generation?

### Answer

A generic numeric generator can create technically valid numbers, but the values may be unrealistic for the source column.

For example:

- `age` should not become `843212`,
- `quantity` should not become `500000`,
- `amount` should not always use a broad banking fallback range if the source profile shows a narrow product-specific range.

Using the profiled minimum and maximum gives the engine a hard boundary learned from the source. That immediately improves realism without introducing a heavy model-training path.

### Question

How does the numeric range path work?

### Answer

For numeric columns, the value generator now checks the column profile before the domain provider.

If the profile has parseable numeric bounds:

1. parse `min_value` and `max_value` as decimals,
2. normalize reversed bounds defensively,
3. return an integer if both bounds are integer-like,
4. return a rounded float when the bounds are decimal-like,
5. fall back to the existing provider if bounds are missing or invalid.

This keeps the generator robust. A bad profile snapshot should not crash a full run; it should simply lose that optimization and continue through the deterministic fallback path.

### Question

Is this full distribution matching?

### Answer

No. This is range-aware generation, not histogram-aware generation.

It guarantees generated numeric values stay within observed bounds. It does not yet preserve whether the source column is normally distributed, skewed, clustered around a few values, or seasonal.

That is why the optimization plan now separates:

- numeric range sampling from min/max,
- deeper numeric distribution-aware sampling.

This keeps the implementation honest and makes future quality work easier to reason about.

## Decision: generate datetime values inside profiled source ranges

### Question

Why handle datetime ranges separately from generic datetime generation?

### Answer

Generic datetime generation can create valid timestamps, but they may land in the wrong business period.

If a source table contains activity from January 2024 through March 2024, generating timestamps in a fixed default year makes the data look less like the source. Profiled min/max datetime hints give the engine the observed time window.

### Question

How does the datetime range path work?

### Answer

For datetime columns, the generator now:

1. reads `min_value` and `max_value` from the column profile,
2. parses common database timestamp strings,
3. normalizes naive timestamps to UTC,
4. samples a deterministic offset inside the observed range,
5. falls back to the generic datetime provider if the profile is missing or invalid.

The parser accepts ISO-style timestamps, `Z` UTC suffixes, date-only values, and common hour-only timezone offsets returned by database text casts.

### Question

Does this preserve seasonality?

### Answer

Not yet.

Min/max only tells us the outer time window. It does not tell us whether the source has weekday spikes, month-end load, holiday seasonality, or time-of-day clustering.

To support seasonality properly, the profiler needs temporal buckets, such as:

- counts by hour of day,
- counts by day of week,
- counts by month,
- counts by business event period.

That is why datetime range sampling is complete now, while datetime seasonality remains a separate optimization task.
