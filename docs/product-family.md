# DataBoom Product Family

DataBoom is the parent platform. It has two main product families:

- `Generator-Boom`: creates synthetic data from schemas, prompts, profiles, and future document/graph specifications.
- `Masker-Boom`: redacts, masks, tokenizes, or replaces sensitive data while preserving referential integrity and useful structure.

The split matters because generation and masking solve related but different problems. Generator-Boom creates safe data from scratch. Masker-Boom transforms existing sensitive data into safer data.

## Product Map

| Product | Status | Purpose |
| --- | --- | --- |
| DataBoom | Active parent platform | Shared API, CLI, docs, deployment, roadmap, and operator experience. |
| Generator-Boom | Active | Synthetic data generation suite. This is the current implementation focus. |
| Masker-Boom | Planned | Privacy and masking service layer for sensitive source data. |

## Generator-Boom Modules

| Module | Status | Use Case |
| --- | --- | --- |
| Schema-Boom | Active | PostgreSQL-first schema-aware relational generation with primary-key and foreign-key integrity. |
| Bank-O-Boom | Active demo profile | Banking, fintech, accounts, balances, merchants, currencies, and transactions. |
| Health-Boom | Active demo profile | Patient, encounter, vitals, diagnosis, and insurance-like clinical datasets. |
| Boom-Commerce | Planned | Ecommerce customers, carts, orders, payments, refunds, promotions, and inventory. |
| Auto-Boom | Planned | Automotive, fleet, insurance, service, claims, and telematics-style datasets. |
| Docu-Boom | Phase 2 planned | NoSQL document data, nested JSON, NDJSON, arrays, object IDs, and references. |
| Graph-Boom | Phase 3 planned | Nodes, edges, labels, properties, connected datasets, and graph exports. |

## Masker-Boom Modules

| Module | Status | Use Case |
| --- | --- | --- |
| Classify-Boom | Phase 4 planned | Detect likely sensitive fields and classify personal, financial, medical, and customer data. |
| Redact-Boom | Phase 4 planned | Remove or redact fields that should not leave a protected environment. |
| Token-Boom | Phase 4 planned | Replace sensitive values with stable tokens while preserving joins and repeatability. |
| Shape-Boom | Phase 4 planned | Preserve distributions, null rates, formats, and relationship structure after masking. |
| Audit-Boom | Phase 4 planned | Produce privacy reports, policy decisions, and run audit trails. |

## Naming Rules

- Product names use Title Case in prose: `Generator-Boom`, `Masker-Boom`, `Bank-O-Boom`.
- Code package names stay boring and stable: `databoom`, not `generator_boom`.
- Domain enum values stay machine-friendly: `financial`, `healthcare`, and `general`.
- Demo folders can use product-style slugs: `demo/bank-o-boom` and `demo/health-boom`.
- User-facing roadmap entries should mention product families when the distinction matters.

## Current Scope

The current implementation is Generator-Boom, specifically Schema-Boom with Bank-O-Boom and Health-Boom demo profiles.

Masker-Boom is intentionally planned for Phase 4 because it needs a reliable schema engine, relationship handling, profiling, validation, policy model, and audit trail before it can safely transform sensitive source data.
