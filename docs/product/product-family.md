# DataBoom Product Family

DataBoom is the parent platform. Its catalog has four main products:

| Product | Data Surface | Status | Purpose |
| --- | --- | --- | --- |
| `Table-Boom` | Relational/tabular | Active | Generate PostgreSQL-style relational datasets with primary-key and foreign-key integrity. |
| `Docu-Boom` | NoSQL documents | Active in Phase 2 | Generate MongoDB-style nested JSON/NDJSON collections with document-shaped previews. |
| `Graph-Boom` | Graph nodes and edges | Active in Phase 3 | Generate connected node/edge datasets with labels, properties, and graph validation. |
| `Masker-Boom` | Masking/redaction | Planned for Phase 4 | Redact, tokenize, hash, or synthetically replace sensitive source data while preserving useful structure. |

## Important Naming Rule

Banking, healthcare, ecommerce, SaaS, customer-support, insurance, and similar categories are **use cases** or **demo profiles**. They are not separate catalog products.

For example:

- `Table-Boom` can generate relational banking tables.
- `Table-Boom` can generate relational healthcare tables.
- `Docu-Boom` can generate nested ecommerce order documents.
- `Masker-Boom` can later mask sensitive fintech or medical fields.

This keeps the product architecture clean. Product names describe the data surface or service layer. Demo names describe the business domain.

## Product Kinds

The backend and frontend should branch on product `kind`, not product name:

| Kind | Product | UI Surface |
| --- | --- | --- |
| `relational` | `Table-Boom` | Table navigator, spreadsheet grid, CSV/JSON/SQL artifacts. |
| `document` | `Docu-Boom` | Collection navigator, MongoDB-like JSON document preview, JSON/NDJSON artifacts. |
| `graph` | `Graph-Boom` | Planned node/edge preview and graph export surface. |
| `masking` | `Masker-Boom` | Planned policy, redaction, classification, and audit surface. |

## Current Scope

Phase 1 completed the relational engine foundation.

Phase 2 completes the local product workflow by adding:

- API-backed product catalog and subscriptions,
- persisted users, sessions, subscriptions, and run metadata,
- generic DataBoom workspace with relational and document surfaces,
- backend-owned workspace sources,
- PostgreSQL source connection testing,
- source schema refresh with primary keys, foreign keys, unique constraints, and column metadata,
- optional source profiling for row counts, null rates, cardinality, ranges, and top values,
- Docu-Boom NoSQL document generation and preview,
- local JSON/NDJSON artifacts for document runs,
- documentation and reusable UI/backend contracts for product-kind based rendering.

Graph-Boom is the active Phase 3 implementation target. Masker-Boom remains
visible in the catalog and roadmap, but it is not a runnable transformation
pipeline yet.
