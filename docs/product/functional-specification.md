# Functional Specification

## Product Summary

DataBoom is the parent platform for four catalog products: Table-Boom, Docu-Boom, Graph-Boom, and Masker-Boom. Table-Boom generates relational data, Docu-Boom generates NoSQL document data, Graph-Boom generates graph data, and Masker-Boom will redact, mask, tokenize, or replace sensitive source data while preserving useful structure.

Table-Boom, Docu-Boom, and Graph-Boom are active generation products. PostgreSQL-backed relational generation came first, NoSQL document data completed Phase 2, and graph generation plus assisted plan review completed Phase 3. Masker-Boom starts in Phase 4 after the generation, profiling, validation, and policy foundations are reliable.

The product should help engineers, QA teams, data teams, demo teams, and privacy-aware platform teams create or transform useful datasets without hand-writing fragile fixtures or copying production data casually.

## Product Family

| Product | Role | Current Scope |
| --- | --- | --- |
| Table-Boom | Generate relational/table data from schemas and profiles. | Active. PostgreSQL-first with CSV, JSON, SQL artifacts and table previews. |
| Docu-Boom | Generate NoSQL document data. | Active. JSON/NDJSON artifacts and document previews. |
| Graph-Boom | Generate graph node and edge data. | Active. Graph JSON/CSV artifacts, validation, previews, and reviewed plans. |
| Masker-Boom | Mask or redact sensitive existing data while preserving useful shape and relationships. | Planned for Phase 4. |

Banking, healthcare, ecommerce, SaaS, insurance, and similar domains are demo use cases or profiles under these products. They are not separate products.

## Problem Statement

Teams need realistic data for development, QA, demos, CI, analytics, and automation. Production data is risky to copy, and simple fixture generators often fail when data must respect primary keys, foreign keys, unique constraints, nullable fields, enums, date ranges, and realistic table relationships.

Table-Boom solves the relational side by understanding schema structure, planning generation, producing valid table data, validating the result, and exporting it in formats that can be loaded or inspected. Docu-Boom solves the document side with nested collection artifacts. Graph-Boom creates validated nodes and endpoint-safe edges. Masker-Boom will solve the adjacent problem of making existing sensitive datasets safer to use without destroying keys, joins, or useful shape.

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
4. DataBoom creates a generation plan through the hosted or deterministic planner.
5. User reviews and approves the plan.
6. User runs the generator.
7. DataBoom validates the generated dataset.
8. User exports SQL or CSV files from local disk.

### Workflow 2: Generate From Existing Database

1. User connects to an existing PostgreSQL database.
2. DataBoom reads schema metadata.
3. DataBoom profiles structural statistics in Phase 2.
4. DataBoom generates synthetic data based on schema and safe summaries.
5. DataBoom validates and exports artifacts.

Masker-Boom privacy-safe replacement is not a Phase 1 or Phase 2 requirement. Field-level privacy policies arrive in Phase 4.

### Workflow 3: CI Fixture Generation

1. CI invokes the CLI with schema, prompt, seed, and output path.
2. DataBoom generates deterministic SQL or CSV artifacts.
3. Validation must pass.
4. CI loads artifacts into a test PostgreSQL database.

### Workflow 4: API-Driven Generation

1. Client submits source metadata, intent, row counts, and formats to the API.
2. API creates and persists a validated plan proposal.
3. Client reviews and approves the plan.
4. API creates an asynchronous generation run linked to that plan.
5. Worker executes generation and validation.
6. Client polls run status and downloads artifacts from local storage.

### Workflow 5: NoSQL Document Data Generation

Implemented in Phase 2.

1. User provides a document collection specification, inferred profile, or NoSQL-oriented prompt.
2. DataBoom builds a document generation plan with nested objects, arrays, identifiers, and references.
3. DataBoom generates JSON or NDJSON artifacts.
4. DataBoom validates document shape, required fields, configured counts, and reference consistency where references exist.

### Workflow 6: Graph Data Generation

Implemented in Phase 3.

1. User provides a graph model, graph-oriented prompt, or table-to-graph mapping.
2. DataBoom plans node labels, edge types, properties, and cardinality.
3. DataBoom generates node and edge artifacts.
4. DataBoom validates edge references, property shape, counts, and export readiness.

### Workflow 7: Mask Existing Sensitive Data

Planned for Masker-Boom in Phase 4.

1. User connects a source dataset or provides exported artifacts.
2. Masker-Boom classifies sensitive fields and maps them to policy actions.
3. User reviews masking rules for redaction, tokenization, hashing, or synthetic replacement.
4. Masker-Boom applies transformations while preserving primary keys, foreign-key relationships, configured formats, and useful distributions.
5. Masker-Boom produces masked artifacts plus a privacy and audit report.

### Workflow 8: Evaluate Source-Trained Synthesis Candidates

Experimental backend workflow introduced in Phase 4. It is intentionally local
and single-table until the privacy and production evidence gates are complete.

1. User supplies an approved CSV and a reviewed dataset contract.
2. Every column is classified for training eligibility; unclassified columns
   default to `restricted` and stop the experiment.
3. The worker deterministically creates training, validation, and untouched
   holdout partitions, preserving subject groups when group columns are given.
4. The worker fits the owned empirical and Gaussian-copula baselines and any
   explicitly installed scikit-learn mixture, owned TensorFlow GAN, or CTGAN
   candidates through the same adapter contract.
5. Every candidate samples the same row count using the same evaluation seed.
6. DataBoom reports structural validity, holdout fidelity, diversity, exact
   training-row matches, runtime, reproducibility, lineage, and missing evidence.
7. The tournament can recommend a candidate only for controlled evaluation. It
   cannot approve a production release while privacy attacks, downstream
   utility, signed lineage, calibrated thresholds, and hardened worker isolation
   remain incomplete.

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

Phase 1 and Phase 2 use deterministic local planning. Phase 3 adds optional LLM-assisted proposals behind the same planner interface, strict output validation, human review, and deterministic fallback.

Future statistical planning must also declare:

- generation mode: `scenario_faithful` or `source_faithful`,
- population segments and locale weights,
- requested clusters, sparsity, missingness, outliers, and tail behavior,
- dependencies or correlations that must be preserved,
- downstream utility task where one exists,
- quality, privacy, latency, memory, and cost budgets.

An LLM may translate user intent into this strict contract. It must not bypass
review, quality gates, constraints, or deterministic execution boundaries.

### Domain Profiles

DataBoom should support domain profiles so users can request data optimized for a use case without changing the core engine.

Initial profiles:

- `general`: generic schema-aware data.
- `financial`: banking and financial data such as accounts, balances, currencies, transaction types, merchants, and statuses.
- `healthcare`: patient and clinical data such as medical record numbers, blood types, diagnoses, vitals, and insurance providers.

Domain profiles must remain optional overlays. They should improve semantic realism where possible, while schema constraints, relationship solving, deterministic seeds, and validation stay generic.

### Statistical Quality Modes

DataBoom must label generated data according to its evidence:

- **Scenario-faithful** output follows schema, domain, locale, distribution, and
  edge-case rules without claiming to have learned production behavior.
- **Source-faithful** output is trained or calibrated from approved source data
  and evaluated against an untouched holdout.

The source-trained path should support a portfolio of deterministic,
statistical, mixture, and optional neural synthesizers. It must select candidates
through measured fidelity, coverage, utility, privacy, performance, and
reproducibility gates. No single model is assumed to be best for every dataset.

The first experimental implementation provides deterministic dataset splitting,
versioned quality intent and bounded Profile v2 artifacts, independent empirical
and owned Gaussian-copula baselines, an optional scikit-learn Gaussian-mixture
baseline, an owned optional TensorFlow GAN, an optional CTGAN provider,
machine-readable quality reports, and candidate-failure isolation. Every
tournament retains shared training/holdout profiles and one synthetic profile per
completed candidate. The copula, mixture, and neural candidates provide joint
model mechanisms, but current profile summaries are not calibrated promotion
gates and the evaluator does not yet provide sufficient relational, temporal,
graph-native, utility, or formal privacy evidence for production claims.

For international populations, country or locale mixtures must be explicit or
learned from an approved profile. Locale may control coherent names, addresses,
phones, dates, postcodes, currencies, and timezones. It must not be used to infer
protected traits through stereotypes.

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

Statistical validation must remain separate from structural validation. A run
can be structurally valid while statistically poor, or statistically similar
while violating a hard business constraint. Source-trained releases require a
quality report with univariate, joint, coverage, shape-specific, utility,
privacy, performance, and lineage evidence appropriate to the use case.

### Masking

Masker-Boom must eventually:

- classify likely sensitive fields,
- redact values that should not be retained,
- generate stable replacement tokens where joins must survive,
- preserve referential integrity across masked tables,
- preserve useful formats, null rates, and distributions where policy allows,
- prevent raw sampled values from leaking into logs or reports,
- produce machine-readable privacy and audit reports.

### Outputs

Phase 1 outputs:

- CSV files per table.
- SQL insert files.
- JSON files per table.
- JSON validation report.
- Local artifact manifest.

Additional current and later outputs:

- direct PostgreSQL load,
- NDJSON and nested JSON document artifacts, `implemented`
- graph node and edge artifacts, `implemented`
- Parquet,
- framework fixture formats.

## MVP Boundaries

The early phases must not attempt to solve everything.

In scope for the current roadmap:

- PostgreSQL first.
- NoSQL document generation starts in Phase 2.
- Graph data generation starts in Phase 3.
- Masker-Boom starts in Phase 4.
- Backend engine first.
- CLI-first local generation.
- API foundation.
- Local disk artifacts.
- 100k records in Phase 1, moving toward 500k in Phase 2.

Out of scope until later:

- Masker-Boom implementation before Phase 4,
- broad database cloning across many vendors,
- object storage,
- perfect business-domain semantics,
- production database mutation,
- custom model training before the statistical quality contracts, holdout
  evaluation, baseline synthesizers, and candidate promotion policy exist,
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
- Masker-Boom can produce integrity-preserving masked artifacts by Phase 4.
- SQL and CSV exports are usable.
- Validation reports are clear and machine-readable.
- CLI and API workflows are documented.
- Docker deployment works by the production phases.
- Scenario-faithful and source-faithful outputs are labeled honestly.
- A source-trained candidate is evaluated on untouched holdout data and passes
  structural, quality, privacy, performance, and reproducibility gates.
- Clusters, sparsity, missingness, outliers, correlations, and international
  population mixtures can be represented through reviewed typed intent.
