# High-Level Design

DataBoom is designed as a product platform, not a single hard-coded generator. The extension point is the data surface: relational tables, document collections, graph nodes/edges, and masking policies.

This document is the canonical system architecture for DataBoom. It describes
services and trust boundaries, not individual Python methods. For module-level
ownership, runtime state, and artifact processing, see [Low-Level Design](low-level-design.md).

## System Context

```mermaid
flowchart LR
    Visitor[Public website visitor] --> PublicSite[Next.js public site]
    Operator[Authenticated workspace user] --> Dashboard[Next.js dashboard]
    Developer[Developer or CI] --> CLI[Typer CLI]

    PublicSite --> Auth[Login or register]
    Auth --> Dashboard
    Dashboard --> API[FastAPI API]
    CLI --> Engine[DataBoom engine]
    API --> Engine

    API --> AsyncRuns[AsyncRunManager local background runs]
    AsyncRuns --> Engine
    API --> StateStore[StateStore boundary]
    StateStore --> MetadataDB[(PostgreSQL or Supabase metadata)]
    API --> Redis[(Redis future run/cache helper)]

    Engine --> Artifacts[(Local artifacts)]
    Engine --> SourceDB[(Optional source PostgreSQL)]
    SourceDB --> Introspection[Schema introspection and profiling]
    Introspection --> Engine
```

The public site explains the platform. The authenticated dashboard executes product workflows. The CLI remains the fastest local and CI path. Both API and CLI call the same backend engine boundaries wherever possible.

## Product Surface Model

```mermaid
flowchart TD
    Catalog[Product catalog entry]
    Catalog --> Kind{product.kind}

    Kind -->|relational| TableBoom[Table-Boom]
    Kind -->|document| DocuBoom[Docu-Boom]
    Kind -->|graph| GraphBoom[Graph-Boom]
    Kind -->|masking| MaskerBoom[Masker-Boom planned]

    TableBoom --> TableContracts[DDL schema model relationship graph generation plan]
    DocuBoom --> DocumentContracts[Collection spec field spec object IDs nested arrays references]
    GraphBoom --> GraphContracts[Node labels edge types properties cardinality]
    MaskerBoom --> MaskingContracts[Policy classification tokenization redaction audit]

    TableContracts --> SharedRun[Shared run metadata artifacts validation preview]
    DocumentContracts --> SharedRun
    GraphContracts --> SharedRun
    MaskingContracts --> SharedRun
```

Banking, healthcare, ecommerce, insurance, and SaaS are use cases. They should be represented as schemas, profiles, demo folders, prompt presets, or catalog metadata under a product. They should not become separate engines unless they introduce a new data surface.

## Engine Pipeline

```mermaid
flowchart TD
    Request[Generation intent and metadata] --> ProductResolver[Resolve product and source contract]
    ProductResolver --> PlannerBoundary[Planner interface]
    PlannerBoundary --> ProviderPolicy{Provider policy}
    ProviderPolicy -->|user or platform key| StructuredPlanner[Structured-output planner]
    ProviderPolicy -->|no key or provider failure| LocalPlanner[Deterministic planner]
    StructuredPlanner --> Proposal[Validated PlanProposal]
    LocalPlanner --> Proposal
    Proposal --> PlanStore[(Per-user plan state)]
    PlanStore --> Review{Operator review}
    Review -->|rejected| Revise[Revise intent]
    Review -->|approved| ExecutionAdapter[Approved-plan execution adapter]

    subgraph RelationalPath[Relational path]
        DDL[DDL or live schema] --> SchemaIngestor[Schema ingestor]
        SchemaIngestor --> RelationshipGraph[Relationship graph]
        RelationshipGraph --> RelationalPlan[Relational generation plan]
    end

    subgraph DocumentPath[Document path]
        DocumentSpec[Document collection specs] --> DocumentPlan[Document generation plan]
    end

    subgraph GraphPath[Graph path]
        GraphSpec[Graph node and edge specs] --> GraphPlan[Graph generation plan]
    end

    ExecutionAdapter --> RelationalPlan
    ExecutionAdapter --> DocumentPlan
    ExecutionAdapter --> GraphPlan
    RelationalPlan --> SeedManager[Deterministic seed manager]
    DocumentPlan --> SeedManager
    GraphPlan --> SeedManager
    SeedManager --> Runtime[Run context]
    Runtime --> Generator[Generator]
    Generator --> Exporter[Artifact exporter]
    Exporter --> Validator[Validator]
    Validator --> Manifest[Manifest and validation report]
```

The planner controls only a small, validated decision: resource names, target
counts, strategies, constraints, warnings, seed, and formats. It does not emit
bulk records and cannot execute a run. Generation remains deterministic and
product-specific after approval, so provider availability and model behavior do
not become data-integrity dependencies.

The engine is extendable because each product kind owns its input model and generation strategy, while shared concerns remain reusable:

- catalog resolution,
- seed management,
- artifact root conventions,
- manifests,
- run metadata,
- validation reports,
- API artifact downloads,
- frontend preview routing.

## API Run Flow

```mermaid
sequenceDiagram
    participant UI as Frontend workspace
    participant API as FastAPI API
    participant Planner as Planning service
    participant Catalog as Product catalog
    participant Engine as Generation engine
    participant Store as StateStore
    participant Disk as Local artifacts

    UI->>API: POST /auth/register or /auth/login
    API->>Store: verify password hash and save bearer session
    UI->>API: POST /subscriptions
    API->>Catalog: validate product and plan
    API->>Store: save subscription
    UI->>API: POST /products/{product_id}/plans
    API->>Catalog: resolve product and source metadata
    API->>Planner: propose validated plan
    Planner-->>API: draft PlanProposal and safe telemetry
    API->>Store: persist plan for authenticated user
    API-->>UI: plan summary, counts, warnings, planner metrics
    UI->>API: POST /plans/{plan_id}/review approved
    API->>Store: persist terminal review decision
    UI->>API: POST /plans/{plan_id}/runs/async
    API->>Store: verify ownership, subscription, and approval
    API->>Catalog: map approved plan to product run request
    API->>Store: save running run metadata
    API-->>UI: running response with plan_id and ETA
    API->>Engine: execute product generation in background
    Engine->>Disk: stream artifacts and flush preview rows
    UI->>API: GET /runs/{run_id}
    API-->>UI: progress and operation timings
    UI->>API: GET preview/artifacts
    API-->>UI: top records and current download links
    Engine->>Disk: write manifest and validation
    API->>Store: save completed run metadata
```

### Planning Trust Boundary

```mermaid
flowchart LR
    Metadata[Schema and resource metadata] --> PromptBuilder[Versioned prompt pack]
    Intent[User intent and row targets] --> PromptBuilder
    PromptBuilder --> Model[Optional hosted model]
    Model --> StrictSchema[Strict JSON schema]
    StrictSchema --> Pydantic[Pydantic validation]
    Pydantic --> ResourceCheck[Exact resource and kind check]
    ResourceCheck --> Draft[Draft plan]
    Draft --> Human[Human approval]
    Human --> Engine[Deterministic engine]

    SourceRows[(Source row values)] -. never sent .-> Model
    ApiKey[User API key] -. memory only .-> Model
```

Stable instructions, output schema, and examples are loaded from a versioned
package prompt pack. Variable source metadata and intent come last. The schema
fingerprint and prompt-pack version form a non-sensitive cache key. Telemetry
records token counts, cached tokens, latency, mode, and fallback reason without
recording prompts, keys, or source values.

## Workspace Source Flow

```mermaid
sequenceDiagram
    participant UI as Dashboard
    participant API as FastAPI API
    participant SourceDB as Source PostgreSQL
    participant Store as StateStore
    participant Engine as Generation engine

    UI->>API: POST /workspace-sources/test-connection
    API->>SourceDB: SELECT 1
    API-->>UI: connection ok or error
    UI->>API: POST /workspace-sources
    API->>Store: persist source shell
    UI->>API: POST /workspace-sources/{source_id}/refresh
    API->>SourceDB: inspect schemas, columns, PKs, FKs, uniques
    API->>Store: save resource metadata and DDL snapshot
    UI->>API: POST /workspace-sources/{source_id}/profile
    API->>SourceDB: row counts, nulls, distinct counts, ranges, top values
    API-->>UI: profile snapshot
    UI->>API: POST /products/{product_id}/plans with source_id
    API->>Store: resolve refreshed source contract
    API-->>UI: reviewable source-shaped plan
    UI->>API: approve plan and start async run
    API->>Engine: generate from source DDL snapshot
```

This makes the engine extendable because the dashboard does not send ad hoc table lists. It selects a persisted source, and the backend uses the refreshed schema contract for planning and generation.

## Frontend Route Architecture

```mermaid
flowchart TD
    Root[/ public home] --> Products[/products public product catalog]
    Root --> Demos[/demos public demo data]
    Root --> Roadmap[/roadmap public roadmap]
    Root --> Contact[/contact public contact]
    Root --> Login[/login]

    Login --> Dashboard[/dashboard authenticated workspace]
    Dashboard --> ProductDetail[/products/[productId] authenticated product run page]
    Dashboard --> Runs[/runs authenticated run history]
    Runs --> RunDetail[/runs/[runId] authenticated run output]
    Dashboard --> Settings[/settings authenticated settings]
    Settings --> Subscriptions[/settings/subscriptions product access]

    Dashboard --> DataWorkspace[DataWorkspace component]
    DataWorkspace --> RelationalSurface[Table grid for relational products]
    DataWorkspace --> DocumentSurface[JSON cards for document products]
    DataWorkspace --> GraphSurface[Node and edge preview]
    DataWorkspace --> PlanReview[Plan proposal and approval]
    DataWorkspace --> PlannedSurface[Planned state for masking]
```

The public pages should contain core product marketing and knowledge. The authenticated routes should contain operational workflow: subscribe, generate, preview, download, and inspect runs.

## Deployment Topology

### Local Docker

```mermaid
flowchart LR
    Browser[Browser] --> NextDev[Next.js frontend]
    NextDev --> API[FastAPI container]
    API --> Postgres[(PostgreSQL container)]
    API --> Redis[(Redis container)]
    API --> ArtifactVolume[(Local artifact volume)]

    subgraph DockerCompose[Docker Compose]
        API
        Postgres
        Redis
        ArtifactVolume
    end
```

Local deployment uses Docker Compose for FastAPI, PostgreSQL, and Redis. Next.js runs as the local frontend during development.

### Render, Supabase, And Vercel

```mermaid
flowchart LR
    Browser[Browser] --> Vercel[Next.js on Vercel]
    Vercel --> Render[FastAPI engine on Render]
    Render --> Supabase[(Supabase Postgres)]
    Render --> ArtifactDisk[(Render container disk)]
    Render --> LLMPolicy{LLM provider policy}
    LLMPolicy --> PlatformKey[Platform key]
    LLMPolicy --> UserKey[User key per request]
    LLMPolicy --> Deterministic[Deterministic fallback]
```

Render runs the Python API and generation engine. Supabase stores users,
sessions, subscriptions, sources, profiles, plans, and run metadata through the
existing `StateStore` boundary. Vercel hosts the public site and dashboard. The
LLM policy is optional: user key first, platform key second, deterministic
fallback always available.

For exact environment variables and smoke tests, see [Deployment Guide](../operations/deployment.md).

## Run Observability

The API exposes a lightweight asynchronous run lifecycle:

- `POST /products/{product_id}/plans` creates a reviewable proposal.
- `POST /plans/{plan_id}/runs/async` creates a run only after approval.
- `GET /runs/{run_id}` returns status, generated rows, current resource, progress percentage, rows per second, expected seconds, remaining seconds, and operation timings.
- Table previews read flushed CSV rows while generation is still running.
- Document previews read completed JSON arrays or partially flushed NDJSON lines.
- Graph previews read generated graph JSON or node/edge CSV files after a graph run.
- Completed relational runs report timings for schema parsing, plan building, export, validation, and total runtime.

The current `AsyncRunManager` is intentionally in-process. It is enough for local MVP workflows, demos, and frontend progress polling. A production worker queue can replace this boundary later without changing the frontend run contract.

## Source Observability

Phase 2 source workflows expose separate operations so the dashboard can show where time and risk sit:

- connection test checks that credentials and network access work before a source is saved or refreshed,
- schema refresh captures table names, schema names, columns, primary keys, foreign keys, unique constraints, a DDL snapshot, and a refresh timestamp,
- source profiling scans selected tables for row counts, null rates, distinct counts, min/max values, and top values,
- product runs can reference a `source_id`, allowing the engine to generate from the refreshed source contract.

These operations are separate on purpose. A quick schema refresh should not always scan table data, and a profiling scan should be an explicit operator action.

## How To Add A New Product Kind

1. Add or extend the product kind enum and API response contract.
2. Add a catalog entry with defaults, output formats, status, features, and use cases.
3. Add an internal spec/model for the new data surface.
4. Add a generator service that returns the shared run response shape.
5. Add validation and artifact export logic for that surface.
6. Add preview endpoints when the data shape needs a custom preview, such as document or graph runs.
7. Add a frontend surface component selected by `product.kind`.
8. Add focused tests for catalog, generation, preview, artifact, and planned-state behavior.

This sequence keeps the platform extendable without scattering product-name conditionals across routes or UI pages.
