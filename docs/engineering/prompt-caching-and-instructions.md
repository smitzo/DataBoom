# Prompt Caching and Instructions

This document defines how DataBoom should structure prompts, reusable instructions, and agent context so OpenAI requests can benefit from prompt caching while remaining maintainable.

## Objectives

- Keep durable instructions stable and versioned.
- Put reusable prompt content before volatile run-specific content.
- Track cache efficiency through usage metrics.
- Maintain prompt files and agent instructions as first-class project artifacts.
- Avoid mixing generated schema samples, timestamps, request IDs, or user-specific data into stable prompt prefixes.

## OpenAI Prompt Caching Rules to Design Around

OpenAI prompt caching works best when repeated requests share an exact prompt prefix. Recent OpenAI models support automatic prompt caching for eligible prompts, and cache hits require stable content at the beginning of the request.

DataBoom should structure LLM-assisted planning requests in this order:

1. Stable system and developer instructions.
2. Stable planner contract and output schema.
3. Stable examples and benchmark prompts.
4. Stable schema summary format.
5. Variable schema instance, user prompt, row counts, seed, and run options.

Do not place timestamps, request IDs, tenant-specific metadata, random values, sampled source data, or temporary debug context before the stable prompt blocks.

## Cache-Friendly Prompt Layout

Use this logical layout when Phase 2 or Phase 3 introduces LLM-assisted planning:

```text
[stable] Product role and safety boundaries
[stable] Planner responsibilities
[stable] Output JSON schema
[stable] Generation constraints and examples
[stable] Known database/type mapping rules
[mostly stable] Normalized schema summary format
[variable] Current schema summary
[variable] User generation prompt
[variable] Row targets, seed, export format, and run options
```

The planner should return a structured generation plan. It should not directly generate the final dataset.

Generation products and Masker-Boom should use separate prompt packs because generation and masking have different safety boundaries. Table-Boom, Docu-Boom, and Graph-Boom prompts produce data plans; Masker-Boom prompts should eventually produce policy suggestions, classification hints, or review summaries, never raw sensitive data.

## Prompt Cache Keys

When using OpenAI API support for prompt cache keys, DataBoom should derive keys from stable non-sensitive identifiers:

```text
databoom:{product_family}:{planner_version}:{schema_fingerprint}:{prompt_pack_version}
```

Rules:

- Never include raw database values.
- Never include secrets, connection strings, user emails, or organization names unless explicitly approved.
- Use product-family namespaces such as `table-boom`, `docu-boom`, `graph-boom`, or `masker-boom`.
- Use a schema fingerprint based on normalized metadata, not sampled data.
- Rotate the key when the stable prompt pack changes.
- Log cache usage metrics, not prompt contents.

## Prompt Files

Future implementation should store reusable prompts under a dedicated prompt pack directory, for example:

```text
prompts/
  planner/
    system.md
    developer.md
    output-schema.json
    examples.md
    version.txt
```

Prompt packs must be treated like code:

- reviewed in pull requests,
- tested against benchmark prompts,
- versioned,
- included in release notes when behavior changes,
- kept free of customer data.

## Benchmark Prompt Set

These prompts define the first benchmark set for planner and generator behavior:

1. "Given this PostgreSQL schema, generate 500 users, 120 organizations, and realistic memberships while preserving all foreign keys."
2. "Create ecommerce demo data with customers, addresses, products, orders, payments, and refunds for the last 18 months."
3. "Generate 10,000 invoice records with line items, taxes, discounts, payment states, and overdue edge cases."
4. "Create a tiny dataset for documentation with 5 companies, 12 users, and enough related records to demonstrate the product."
5. "Generate boundary cases: null optional values, maximum string lengths, old dates, future dates, and zero-value amounts."
6. "Create a dataset where every project has between 2 and 6 tasks, each task has comments, and all users belong to valid teams."
7. "Generate CSV files per table and a validation report without writing to any database."
8. "Create SQL inserts that can be loaded into a clean PostgreSQL database in dependency order."

Masker-Boom privacy prompts are intentionally deferred until Phase 4.

## Instruction Caching for Codex

Codex discovers persistent repository guidance through `AGENTS.md`. Keep project-wide agent behavior there and keep task-specific instructions in the user prompt.

Guidelines:

- Keep `AGENTS.md` stable and concise.
- Put durable project rules, phase priorities, commit labels, and verification expectations in `AGENTS.md`.
- Put large design details in `docs/` and link to them from `AGENTS.md`.
- Do not paste volatile task state into `AGENTS.md`.
- Restart Codex or begin a fresh task after changing `AGENTS.md` when you need the new instructions loaded.
- If future docs become large, split specialized guidance into nested `AGENTS.md` files near the relevant source tree.

## Metrics to Capture

Once LLM planning is implemented, each LLM request should record:

- model,
- prompt pack version,
- schema fingerprint,
- prompt cache key,
- total input tokens,
- cached input tokens,
- cache write tokens when available,
- output tokens,
- latency,
- planner success/failure,
- validation outcome after generation.

These metrics should be structured logs and should not include raw prompts by default.

## Documentation Maintenance

Update this file whenever:

- planner prompt layout changes,
- OpenAI model family changes,
- prompt cache key strategy changes,
- output plan schema changes,
- benchmark prompts change,
- Codex repository guidance changes.
