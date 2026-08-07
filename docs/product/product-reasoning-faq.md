# Product Reasoning and FAQ

This document explains why DataBoom exists, where it fits, and how to answer common strategic and technical questions. Use it when pitching, reviewing scope, onboarding engineers, or deciding whether a feature belongs in the engine.

## Short Positioning

DataBoom is not just a fake-value generator and not just a chat prompt. It is a platform for four related data products: Table-Boom creates relational synthetic data, Docu-Boom creates NoSQL document data, Graph-Boom will create graph data, and Masker-Boom will transform sensitive existing data into safer datasets while preserving integrity.

The platform should eventually serve sensitive domains such as fintech, healthcare, insurance, SaaS, customer support, internal operations, and analytics. Phase 1 focuses on Table-Boom's relational generation engine first. Phase 2 expands into Docu-Boom NoSQL document data, Phase 3 adds Graph-Boom data, and Masker-Boom privacy, masking, hashing, tokenization, and policy enforcement arrive in Phase 4 once the core generation paths are reliable.

## Product Families

### What are Table-Boom, Docu-Boom, and Graph-Boom?

They create synthetic data from scratch for different data surfaces. Table-Boom handles relational tables, Docu-Boom handles nested NoSQL documents, and Graph-Boom will handle nodes and edges. Banking, healthcare, ecommerce, and similar domains are use cases or demo profiles under those products.

### What is Masker-Boom?

Masker-Boom is the planned masking service layer. It will classify sensitive fields, redact values, tokenize identifiers, replace values synthetically, preserve joins, and produce privacy/audit reports. It is for teams that already have sensitive data but need safer copies for development, QA, analytics, or AI workflows.

### Why split them?

Generation and masking are related but not identical. Table-Boom, Docu-Boom, and Graph-Boom can create fresh synthetic data with no source records. Masker-Boom starts from source data and must preserve enough structure to remain useful while removing or replacing sensitive values. Keeping the product responsibilities separate makes scope, safety, and customer promises clearer.

## 4W1H Product Questions

### Who needs DataBoom?

- Backend teams that need realistic local and staging databases.
- QA teams that need repeatable edge cases and large test runs.
- Data teams that need analytical datasets without using raw production data.
- Fintech and healthcare teams that cannot casually copy sensitive records.
- Demo teams that need believable relational data, not random isolated rows.
- AI and automation teams that need structured corpora with valid joins.

### What problem does it solve?

DataBoom solves the gap between simple fake-data scripts and production-like databases. Most teams can create random names, dates, and emails. The hard part is creating many tables where every row still obeys schema constraints, foreign keys, unique keys, cardinality rules, and business-like distributions.

### Where is it useful?

- Local development databases.
- Staging and QA environments.
- CI fixture generation.
- Demo environments.
- Load testing.
- Analytics sandboxing.
- Regulated workflows where direct production copies are not acceptable.
- Pre-production data modeling before real customer data exists.

### When should teams use it?

Use DataBoom when data must be:

- relationally valid,
- reproducible,
- large enough for meaningful tests,
- exportable,
- validated,
- explainable,
- generated repeatedly in CI or developer workflows.

Do not use it as the first solution when a team only needs five simple records for a unit test. In that case, hand-written fixtures are usually clearer.

### Why is a dedicated engine needed?

A dedicated engine is needed because large relational data generation is a systems problem, not only a text-generation problem. The engine must parse schemas, solve dependency order, generate values, preserve foreign keys, stream output, validate constraints, store artifacts, expose API/CLI workflows, and produce repeatable results under operational limits.

### How does DataBoom solve it?

DataBoom splits the generation problem into specialized components:

- schema ingestion understands database structure,
- relationship solving computes table order and foreign-key sources,
- deterministic generation creates repeatable rows,
- chunked exporters avoid holding every row in memory,
- validators prove the result can be loaded,
- prompt planners translate intent into controlled generation plans,
- Masker-Boom later adds privacy policies that protect sensitive fields.

### Where do NoSQL and graph data fit?

PostgreSQL relational generation is the first foundation because foreign keys, dependency ordering, and validation are the hardest core problems to prove early. Phase 2 should add Docu-Boom NoSQL document data once the API, scaling, and profiling foundations are stronger. Phase 3 should add Graph-Boom once planning and operator review are mature enough to reason about nodes, edges, properties, and cardinality.

This keeps scope disciplined:

- Phase 1 proves relational correctness.
- Phase 2 adds Docu-Boom document-style generation for JSON, NDJSON, and MongoDB-like use cases.
- Phase 3 adds Graph-Boom connected graph generation for node and edge datasets.
- Phase 4 adds Masker-Boom for sensitive-data masking and privacy policies.

## Why Not Just Use Faker?

Faker is useful, and DataBoom should use Faker where it helps. But Faker is a value library, not a complete relational, document, graph, or masking engine.

Faker can generate:

- names,
- emails,
- addresses,
- dates,
- phone numbers,
- text,
- simple randomized values.

Faker does not, by itself, solve:

- PostgreSQL schema parsing,
- table dependency ordering,
- foreign-key preservation,
- many-to-many join generation,
- composite uniqueness,
- deterministic multi-table generation plans,
- chunked SQL/CSV export,
- validation reports,
- API/CLI run management,
- large artifact handling,
- privacy policy enforcement.

DataBoom should use Faker as one ingredient inside the generator, then add the missing engine layer around it.

## Why Not Just Ask ChatGPT To Generate 1 Million Records?

ChatGPT or an LLM can help plan data, infer domain rules, produce examples, and explain schemas. It should not be responsible for directly writing one million records in a chat response.

Direct LLM generation is the wrong tool for million-row output because:

- output windows are limited,
- long responses are slow and expensive,
- one broken row can invalidate an entire load,
- maintaining exact foreign-key integrity across millions of tokens is unreliable,
- streaming files, manifests, retries, and validation need program control,
- deterministic seeded regeneration requires an execution engine,
- sensitive-data workflows need auditability and policy enforcement,
- generated artifacts must be written to disk or loaded into databases, not pasted into chat.

The better architecture is to let the LLM help create or refine a generation plan, then let the deterministic engine execute that plan.

## How Can DataBoom Handle 1 Million Records?

One million records is achievable when generation is treated as a streaming data pipeline.

DataBoom should handle large runs through:

- dependency-ordered table generation,
- deterministic primary-key ranges,
- bounded foreign-key registries,
- chunked row generation,
- streaming CSV/SQL writers,
- artifact manifests,
- chunk-aware validation,
- resumable run metadata in later phases,
- optional direct PostgreSQL `COPY` support in later phases,
- performance benchmarks at 100k, 500k, and then 1M records.

The phase plan intentionally ramps up:

- Phase 1: prove 100k records with streaming-friendly design.
- Phase 2: harden toward 500k records with chunking and profiling.
- Phase 5 or a later scale milestone: validate 1M records as a formal benchmark.

The key is that the engine should never require all rows for all tables to live in memory at once.

## Why Build This If Tonic.ai Exists?

Tonic.ai is a mature commercial synthetic data platform. Its public product pages describe capabilities such as generating synthetic data from scratch, sanitizing production data for testing, relational synthetic databases, prompt/schema/sample-driven generation, de-identification, and specialized products for structured and unstructured data.

DataBoom should not claim to be universally better than Tonic.ai. The better claim is that DataBoom is being built for different control points:

- open, inspectable architecture,
- commit-by-commit ownership,
- local-first development,
- simple deployment path for internal teams,
- direct control over schema parsing and generation behavior,
- customizable prompt planning,
- transparent validation reports,
- ability to tune performance for our exact database and CI workflows,
- no dependency on a closed vendor workflow for core test-data generation.

Tonic.ai may be the better choice for teams that need a complete commercial data de-identification platform immediately. DataBoom is valuable when the team wants an owned engine, transparent internals, local deployment, and a roadmap split clearly across Table-Boom, Docu-Boom, Graph-Boom, and Masker-Boom.

References:

- Tonic.ai homepage: https://www.tonic.ai/
- Tonic Fabricate product page: https://www.tonic.ai/products/fabricate
- Tonic.ai product documentation: https://www.tonic.ai/docs

## Why Sensitive Domains Still Matter If Privacy Is Later?

Fintech, medical, insurance, and customer-sensitive SaaS workflows are central use cases. However, Masker-Boom privacy features should be built on top of a correct generation and validation foundation, not before it.

The staged logic is:

1. First, make generation relationally correct.
2. Then, make it scalable and operational.
3. Then, add LLM-assisted planning safely.
4. Then, add Masker-Boom privacy policy enforcement, masking, hashing, tokenization, and audit trails.

This avoids building privacy controls around a weak generator that cannot yet preserve relationships or validate output.

Phase 1 and Phase 2 should avoid claiming production-grade privacy. They can still be useful for non-sensitive schemas, toy datasets, internal demos, synthetic-from-scratch generation, and CI fixtures.

## Additional Questions To Expect

### What makes the generated data trustworthy?

Validation. The engine must check primary keys, foreign keys, required fields, configured row counts, export readiness, and later privacy policy compliance. Trust comes from machine-readable proof, not from hoping random generation worked.

### What makes the generated data realistic?

Realism comes from schema structure, domain-aware column strategies, relationship cardinality, profiling summaries, prompt intent, and later LLM-assisted planning. Realism is not just fake names; it is believable connected behavior across tables.

### What happens when a schema is too complex?

The engine should fail with an explainable plan or validation error. It should identify unsupported constraints, cycles, ambiguous relationships, or columns without safe generation strategies. Silent bad data is worse than a clear refusal.

### What happens when the prompt conflicts with the schema?

Schema safety wins. The planner can explain that the request cannot be fulfilled as written and propose a valid alternative.

### How is this different from database seeding scripts?

Seed scripts are usually application-specific and hand-maintained. DataBoom should be schema-driven, reusable across projects, prompt-guided, exportable, validated, and eventually API-driven.

### Why not start with the frontend?

The core risk is backend correctness: schema parsing, relationships, generation, validation, and scale. A frontend can make the product easier to use, but it cannot compensate for invalid data. That is why Phase 1 starts with the backend engine.
