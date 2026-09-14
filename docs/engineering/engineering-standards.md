# Engineering Standards

DataBoom should stay modular as it grows across relational, document, graph, and masking products. Every backend and frontend change should prefer reusable building blocks over copy-pasted product-specific code.

## Core Rules

- Keep product identity separate from engine implementation. Product names such as `Table-Boom`, `Docu-Boom`, `Graph-Boom`, and `Masker-Boom` belong in catalog/configuration and UI copy, not scattered through core algorithms.
- Share contracts before sharing UI. Backend responses should expose stable fields such as `kind`, `tables`, `collections`, `artifacts`, and `validation` so frontend components can branch from data shape instead of hard-coded product names.
- Prefer reusable helpers for repeated frontend layout patterns, loading states, artifact links, table/document previews, metrics, and run summaries.
- Prefer reusable backend services for generation, export, validation, artifact listing, state persistence, and preview loading.
- Add a product-specific branch only when behavior is truly different. For example, relational data needs table grids, document data needs JSON/NDJSON previews, graph data needs node/edge views, and masking will need policy/audit views.
- Keep generated artifact storage and metadata storage separated. Files stay in local artifacts through Phase 3; API metadata stays behind the state store.
- Keep tests aligned with reusable contracts. Tests should assert product kind, artifact shape, preview behavior, and subscription flow without depending on obsolete demo product names.

## Frontend Standards

- Use component composition instead of route-level monoliths.
- Keep workspace-level state in a single surface component, then delegate display to focused children.
- Render by product `kind`:
  - `relational`: tables, rows, column types, CSV/SQL/JSON artifacts.
  - `document`: collections, JSON documents, NDJSON/JSON artifacts.
  - `graph`: node/edge previews and graph artifact summaries.
  - `masking`: planned policy, classification, redaction, and audit views.
- Keep Tailwind utility styling local to components; do not add raw CSS unless a framework-level global rule is needed.
- Avoid product-name conditionals such as `if product.id === "table-boom"` when `product.kind` or response shape is enough.

## Backend Standards

- Keep API routes thin. Routes should authenticate, validate product access, dispatch to a service, persist the run, and return typed responses.
- Keep product catalog entries declarative. Catalog data can define default counts, schemas/specs, use cases, and status, while runtime behavior lives in services.
- Keep relational and document generation behind separate service functions until a shared planner abstraction genuinely reduces duplication.
- Use Pydantic models for API contracts and dataclasses or typed models for internal immutable catalog/spec definitions.
- Avoid introducing Celery, Kafka, object storage, or heavy orchestration until a concrete Phase 2/3 workflow requires it.

## Product Taxonomy

DataBoom's catalog has four main products:

| Product | Kind | Status |
| --- | --- | --- |
| `Table-Boom` | Relational/tabular data | Active |
| `Docu-Boom` | NoSQL document data | Active in Phase 2 |
| `Graph-Boom` | Graph node/edge data | Active in Phase 3 |
| `Masker-Boom` | Sensitive data masking/redaction | Planned for Phase 4 |

Banking, healthcare, ecommerce, SaaS, and other domains are use cases or demo profiles under these products. They are not separate products.
