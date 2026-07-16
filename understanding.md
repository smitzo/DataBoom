# Boom Data Understanding Log

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

The project was too important to leave as a single rough paragraph. Boom Data needs to become a production-grade synthetic data engine, so the planning documents need separation of concerns. Product behavior, technical design, prompt strategy, and agent rules all change at different speeds and are read by different audiences.

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
- Added reasoning for why Boom Data is more than Faker.
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

The comparison with Faker is framed carefully: Faker is useful, but incomplete. Boom Data should use Faker for fake values while adding schema parsing, relationship solving, streaming, validation, and run management around it.

The comparison with Tonic.ai is also framed carefully. Tonic.ai is a mature commercial platform. Boom Data's argument is not "Tonic is bad"; it is "we need an owned, inspectable, local-first, PostgreSQL-focused engine that we can evolve commit by commit."

The ChatGPT reasoning separates planning from execution. LLMs are strong at interpreting intent and producing plans. They are not the right execution layer for directly emitting huge relational datasets with guaranteed constraints.

### Performance, Reliability, or Maintainability Impact

The reasoning pushes the implementation toward a streaming pipeline. That matters for performance because 100k, 500k, and eventually 1M records cannot be treated as one giant in-memory object.

The documentation also improves reliability. It says schema safety wins over prompt requests, validation is required, and privacy claims should not be made before privacy features exist.

Maintainability improves because significant decisions now explain themselves. A beginner can read this file and understand why important choices were made instead of reverse-engineering intent from code.

### Beginner Explanation

Faker is like a box of fake names and addresses. ChatGPT is like a smart planner that can describe what data should look like. Boom Data needs to be the factory: it reads the database blueprint, decides which tables come first, creates rows in the right order, writes files without running out of memory, and checks that everything fits.

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

PostgreSQL is required because Boom Data is PostgreSQL-first. Redis is useful to have early because it is lightweight and will likely support future run state, locks, queues, caching, or progress tracking. Celery and Kafka are heavier architectural commitments. Adding them before there is a concrete workflow would increase operational complexity without improving the Phase 1 backend engine.

### Details

The Compose file should make local infrastructure easy to start while keeping the application image usable for CLI commands and future API work. The app service is therefore a tool/profile service for now instead of a fake long-running worker. This avoids pretending that Phase 1 already has an API server or background job system.

The important design principle is "prepare the runway, but do not build unused machinery." Redis prepares for future orchestration. Celery or Kafka should wait until there is a specific Phase 2 or Phase 3 need, such as long-running generation jobs, progress events, retries, or distributed workers.

### Follow-Up Notes

- When API run management arrives, decide whether Redis alone is enough or whether Celery is needed.
- Kafka should only be considered if Boom Data needs durable event streams or integration with external event-driven systems.
- The Dockerfile should remain simple until production deployment hardening in Phase 5.

## Decision: normalize schemas before parsing, planning, or generation

### Question

Why does Boom Data need explicit schema model contracts instead of passing raw SQL parser output or dictionaries directly into the generator?

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

Should Boom Data parse PostgreSQL DDL with a SQL parser dependency or with custom string manipulation?

### Answer

Use `sqlglot` for Phase 1 DDL parsing. It gives us a structured AST for common `CREATE TABLE` statements, which is safer than splitting strings by commas, parentheses, and keywords.

### Why This Matters

DDL looks simple until constraints, defaults, nested type parameters, quoted identifiers, and table-level foreign keys appear. A custom parser can accidentally split `decimal(10, 2)` or `UNIQUE (account_id, email)` incorrectly. That kind of bug would corrupt the schema model before generation even starts.

### Details

The ingestion layer should convert SQL parser output into Boom Data's normalized `DatabaseSchema`. The rest of the engine should not depend directly on `sqlglot` expressions. This keeps the parser replaceable if we later need deeper PostgreSQL coverage, live introspection, or a different parser.

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

How should Boom Data decide which table to generate first when schemas contain foreign keys?

### Answer

Build a relationship graph where referenced parent tables point to dependent child tables, then topologically sort that graph. This produces an order where parent rows exist before child rows need to reference them.

### Why This Matters

Foreign-key correctness is the core value of Boom Data. If a child table like `orders` is generated before its parent table `users`, the generator either has to guess IDs or fix data later. Both approaches are risky. A dependency graph makes the correct order explicit before generation starts.

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

How should Boom Data make generated datasets reproducible without forcing every generator to share one global random object?

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

Why should Boom Data build a generation plan instead of immediately generating rows from a schema and row-count dictionary?

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

## Commit: backend: scaffold python package and settings

### What Changed

- Added `pyproject.toml` with the Python package metadata, runtime dependencies, dev dependencies, pytest configuration, Ruff configuration, and the `boom-data` CLI entry point.
- Added `.gitignore` so local virtual environments, caches, build outputs, coverage files, environment files, and generated artifacts do not get committed accidentally.
- Added `.env.example` to document the first environment variables.
- Created the initial `src/boom_data` package layout.
- Added `boom_data.cli` with an `info` command that prints active configuration.
- Added `boom_data.core.config` with Pydantic settings for environment, artifact root, and log level.
- Added `boom_data.core.logging` for shared logging setup.
- Added `boom_data.core.artifacts` for local artifact directory creation.
- Added `tests/test_config.py` to verify settings normalization and artifact path resolution.

### Why It Changed

Phase 1 needs a stable Python backend foundation before schema parsing, relationship solving, generation, and validation can be added. Without the package layout, dependency declaration, settings model, and test runner, later features would be built on loose scripts instead of a maintainable backend.

### Why This Approach

The project uses a `src/` layout because it prevents tests from accidentally importing files from the repository root in ways that differ from an installed package. This catches packaging mistakes earlier.

Pydantic settings are used because Boom Data will eventually run as both a CLI and an API service. Both entry points need the same validated configuration. Starting with settings now avoids scattering environment variable reads throughout the codebase.

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
