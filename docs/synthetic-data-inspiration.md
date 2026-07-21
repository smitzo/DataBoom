# Synthetic Data Inspiration Notes

This document captures product and implementation lessons from adjacent tools. These are inspiration notes, not a plan to copy another product.

## Sources Reviewed

- Tonic.ai product documentation: https://www.tonic.ai/docs
- Tonic Fabricate product page: https://www.tonic.ai/products/fabricate
- Gretel Synthetics repository: https://github.com/gretelai/gretel-synthetics
- generatedata.com: https://generatedata.com/

## Lessons To Apply

### Domain-Specific Datasets

Tonic frames synthetic data around use cases such as software testing, AI training, mock APIs, financial services, and healthcare. Boom Data should similarly treat domain use cases as first-class product concepts.

Current application:

- `general` domain profile.
- `financial` domain profile.
- `healthcare` domain profile.
- demo datasets in `demo/`.

Future direction:

- add domain profile configuration files,
- add profile preview examples,
- let users choose domain intent in the frontend,
- expose profile-specific quality checks.

### Multiple Outputs

Tonic emphasizes exporting into and from many data ecosystems, while generatedata.com makes output format selection part of the simple generation flow.

Current application:

- CSV export,
- SQL export,
- JSON export,
- artifact manifest,
- validation report.

Future direction:

- NDJSON for streaming pipelines,
- Parquet for analytics,
- direct PostgreSQL load,
- object storage adapters.

### Modular Generation Engines

Gretel Synthetics separates different model families and generation approaches. Boom Data should follow that modular idea at an engine level: local rule-based generation first, optional LLM planning later, and specialized providers for domain semantics.

Current application:

- schema model contracts,
- relationship graph,
- generation plan,
- domain value providers,
- row generator,
- exporters,
- validators.

Future direction:

- configurable domain providers,
- LLM-assisted planner,
- privacy policy engine,
- profiling-based statistical providers.

### Simple User Flow

generatedata.com is useful as a workflow reference: choose data types, choose output format, generate data. Boom Data is more relational and production-oriented, but the frontend should preserve this simplicity.

Frontend implication:

- first screen should be an actual workbench,
- show domain, schema, output format, row target, and validation state,
- keep advanced controls available but not dominant,
- make sample datasets visible and easy to inspect.

## Product Guardrails

- Do not claim Boom Data is already a privacy platform in Phase 1.
- Do not position Boom Data as universally better than Tonic or Gretel.
- Keep the differentiator focused on owned, local-first, inspectable, PostgreSQL-first relational generation.
- Use commercial tools as inspiration for workflow clarity, not as implementation dependencies.
