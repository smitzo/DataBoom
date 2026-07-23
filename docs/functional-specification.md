# Functional Specification

## Product Summary

DataBoom generates realistic synthetic data from prompts and PostgreSQL schemas while preserving relational integrity across tables. PostgreSQL-backed relational generation is first; NoSQL document data is planned for Phase 2, and graph data is planned for Phase 3.

The product should help engineers, QA teams, data teams, and demo teams create useful datasets without hand-writing fragile fixtures.

## Problem Statement

Teams need realistic data for development, QA, demos, CI, analytics, and automation. Production data is risky to copy, and simple fixture generators often fail when data must respect primary keys, foreign keys, unique constraints, nullable fields, enums, date ranges, and realistic table relationships.

DataBoom solves this by understanding schema structure, planning generation, producing relationally valid data, validating the result, and exporting it in formats that can be loaded or inspected.

## Target Users

- Backend engineers who need local or staging datasets.
- QA engineers who need repeatable edge-case data.
- Data engineers who need large structured datasets.
- Demo teams who need believable sample data.
- Automation and AI teams who need schema-aware test corpora.
- Fintech, healthcare, insurance, and customer-sensitive SaaS teams that need realistic data without casually copying production records.

## Product Reasoning

See [Product Reasoning and FAQ](product-reasoning-faq.md) for deeper answers to common questions such as why DataBoom needs an engine, why Faker alone is not enough, how this differs from direct ChatGPT generation, how large datasets can be streamed, and how this compares with commercial synthetic data platforms.

## Core User Workflows

### Workflow 1: Generate From Schema

1. User provides PostgreSQL DDL or a live PostgreSQL connection.
2. User provides a generation prompt, row counts, and a seed.
3. DataBoom parses the schema and builds a relationship graph.
4. DataBoom creates a generation plan.
5. User runs the generator.
6. DataBoom validates the generated dataset.
7. User exports SQL or CSV files from local disk.

### Workflow 2: Generate From Existing Database

1. User connects to an existing PostgreSQL database.
2. DataBoom reads schema metadata.
3. DataBoom profiles structural statistics in Phase 2.
4. DataBoom generates synthetic data based on schema and safe summaries.
5. DataBoom validates and exports artifacts.

Privacy-safe replacement is not a Phase 1 or Phase 2 requirement. Field-level privacy policies arrive in Phase 4.

### Workflow 3: CI Fixture Generation

1. CI invokes the CLI with schema, prompt, seed, and output path.
2. DataBoom generates deterministic SQL or CSV artifacts.
3. Validation must pass.
4. CI loads artifacts into a test PostgreSQL database.

### Workflow 4: API-Driven Generation

1. Client submits schema reference and generation request to the API.
2. API creates a generation run.
3. Worker executes generation and validation.
4. Client polls run status.
5. Client downloads artifacts from local storage.

### Workflow 5: NoSQL Document Data Generation

Planned for Phase 2.

1. User provides a document collection specification, inferred profile, or NoSQL-oriented prompt.
2. DataBoom builds a document generation plan with nested objects, arrays, identifiers, and references.
3. DataBoom generates JSON or NDJSON artifacts.
4. DataBoom validates document shape, required fields, configured counts, and reference consistency where references exist.

### Workflow 6: Graph Data Generation

Planned for Phase 3.

1. User provides a graph model, graph-oriented prompt, or table-to-graph mapping.
2. DataBoom plans node labels, edge types, properties, and cardinality.
3. DataBoom generates node and edge artifacts.
4. DataBoom validates edge references, property shape, counts, and export readiness.

## Functional Requirements

### Schema Intake

DataBoom must support:

- PostgreSQL DDL files in Phase 1.
- Live PostgreSQL metadata introspection in Phase 1 or Phase 2.
- NoSQL document specifications or inferred document profiles in Phase 2.
- Graph model specifications for nodes, edges, and properties in Phase 3.
- Normalized internal schema representation.
- Primary keys, foreign keys, nullable fields, defaults, enums, and unique constraints.
- Relationship graph construction.

### Generation Planning

DataBoom must create a plan before generating data.

The plan should include:

- tables to generate,
- data family: relational, document, or graph,
- row counts per table,
- dependency order,
- generation strategy per column,
- foreign-key source mapping,
- seed,
- export formats,
- validation checks.

Phase 1 uses deterministic local planning. LLM-assisted planning can be introduced in Phase 2 or Phase 3.

### Domain Profiles

DataBoom should support domain profiles so users can request data optimized for a use case without changing the core engine.

Initial profiles:

- `general`: generic schema-aware data.
- `financial`: banking and financial data such as accounts, balances, currencies, transaction types, merchants, and statuses.
- `healthcare`: patient and clinical data such as medical record numbers, blood types, diagnoses, vitals, and insurance providers.

Domain profiles must remain optional overlays. They should improve semantic realism where possible, while schema constraints, relationship solving, deterministic seeds, and validation stay generic.

### Relationship-Aware Generation

The engine must:

- generate parent records before child records,
- preserve foreign-key validity,
- support common one-to-many relationships,
- support join tables,
- respect unique primary keys,
- produce repeatable output when the same seed is used,
- avoid loading the full dataset into memory when streaming is practical.

### Validation

Every run must produce a validation report.

Validation should check:

- primary-key uniqueness,
- foreign-key integrity,
- required fields,
- basic type compatibility,
- configured row counts,
- export readiness.

Later phases should add deeper constraint validation, privacy validation, and statistical validation.

### Outputs

Phase 1 outputs:

- CSV files per table.
- SQL insert files.
- JSON files per table.
- JSON validation report.
- Local artifact manifest.

Later outputs:

- direct PostgreSQL load,
- NDJSON and nested JSON document artifacts,
- graph node and edge artifacts,
- Parquet,
- framework fixture formats.

## MVP Boundaries

The early phases must not attempt to solve everything.

In scope for the current roadmap:

- PostgreSQL first.
- NoSQL document generation starts in Phase 2.
- Graph data generation starts in Phase 3.
- Backend engine first.
- CLI-first local generation.
- API foundation.
- Local disk artifacts.
- 100k records in Phase 1, moving toward 500k in Phase 2.

Out of scope until later:

- privacy/masking engine,
- broad database cloning across many vendors,
- graph data before Phase 3,
- object storage,
- perfect business-domain semantics,
- production database mutation,
- custom model training,
- frontend-heavy workflow.

## Acceptance Criteria

DataBoom is useful when:

- A user can point it at a PostgreSQL schema and generate a valid multi-table dataset.
- Generated foreign keys are valid.
- Generation is deterministic with a seed.
- 100k records can be generated in Phase 1 without memory-heavy design.
- 500k records can be generated by Phase 2 with documented performance.
- NoSQL document runs can produce validated JSON or NDJSON artifacts by Phase 2.
- Graph runs can produce validated node and edge artifacts by Phase 3.
- SQL and CSV exports are usable.
- Validation reports are clear and machine-readable.
- CLI and API workflows are documented.
- Docker deployment works by the production phases.
