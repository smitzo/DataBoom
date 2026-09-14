# Phase 3 Closeout

Phase 3 is complete. This handoff records what shipped and the invariants Phase 4
must preserve. Current and future work belongs in the
[Engineering Roadmap](../../engineering/roadmap.md).

## Delivered Scope

### Graph-Boom

- Declarative node, edge, property, endpoint, and artifact contracts.
- Deterministic node IDs, property values, and endpoint-safe edges.
- Graph JSON plus node and edge CSV exports.
- Validation for duplicate node IDs, dangling endpoints, and count mismatches.
- Synchronous and asynchronous product-run integration.
- Top-node and top-edge preview API plus a product-kind-driven frontend preview.

### Assisted Planning

- Provider-neutral `Planner` interface and deterministic implementation.
- Optional structured-output planner through the Responses API.
- Versioned prompt packs shipped as Python package resources.
- Strict output-schema and Pydantic validation before a proposal is persisted.
- Stable schema fingerprints and non-sensitive prompt cache keys.
- Input, cached-input, cache-write, output-token, and latency telemetry.
- Bounded provider timeout/retries and deterministic fallback on every provider
  failure.

### Review And Execution

- Per-user plan persistence through `StateStore`.
- Content-addressed plan IDs for idempotent proposal retries.
- Draft, approved, and rejected review states.
- Generation allowed only from an approved plan.
- `plan_id` propagated into run metadata for traceability.
- Dashboard flow to propose, inspect, reject, approve, and execute a plan.
- User-supplied API keys kept in tab-scoped browser session storage and excluded
  from persisted plan state.

## Phase 3 API Surface

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/products/{product_id}/plans` | Create a reviewable plan proposal. |
| `GET` | `/plans` | List the authenticated user's plans. |
| `GET` | `/plans/{plan_id}` | Inspect one owned plan. |
| `POST` | `/plans/{plan_id}/review` | Approve or reject a draft. |
| `POST` | `/plans/{plan_id}/runs/async` | Execute an approved plan. |
| `GET` | `/runs/{run_id}/graph-preview` | Preview generated nodes and edges. |

## Safety And Reliability Invariants

1. The planner receives metadata and user intent, never source row values.
2. A model proposes a small plan; deterministic engines generate bulk records.
3. Unknown resources, changed resource kinds, invalid counts, and extra output
   fields are rejected before execution.
4. Missing keys, exhausted credits, timeouts, malformed output, and provider
   errors fall back to deterministic planning.
5. API keys, raw prompts, and source values are not written to planner telemetry.
6. Plan review is explicit and terminal; a revised brief creates a new plan.

## Verification Evidence

Phase 3 closes with:

- planner unit and provider-adapter tests,
- API ownership, review, persistence, and execution tests,
- golden planner contracts for relational, document, and graph products,
- Graph-Boom generator, artifact, validation, API, and preview tests,
- backend lint and full pytest suite,
- frontend type checking and production build.

## Accepted Gaps For Phase 4 And Phase 5

- Masker-Boom privacy policies and transformations are not implemented.
- Async generation remains in-process instead of using distributed workers.
- Managed deployments still need durable object storage or a persistent disk.
- Prompt telemetry is logged per request but has no aggregate operations dashboard.
- Graph source profiling, degree-distribution fitting, graph visualization, and
  database-specific graph exports remain future quality work.
