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
    Request[Generation intent metadata and locale] --> ProductResolver[Resolve product and source contract]
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
    ExecutionAdapter --> LocaleContext[Locale-aware row context]

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
    LocaleContext --> RelationalPlan
    LocaleContext --> DocumentPlan
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

Locale is part of the reviewed execution contract, not a suggestion passed to
every generated row. The planner can infer or confirm locale from intent, while a
deterministic row-context provider enforces correlated name, gender, phone, age,
and geography values during Table-Boom and Docu-Boom execution. This keeps the
LLM outside the high-volume path and lets locale catalogues grow independently of
export and validation code.

The engine is extendable because each product kind owns its input model and generation strategy, while shared concerns remain reusable:

- catalog resolution,
- seed management,
- artifact root conventions,
- manifests,
- run metadata,
- validation reports,
- API artifact downloads,
- frontend preview routing.

### Statistical Synthesis Extension Boundary

The current deterministic generator remains the default execution adapter.
Source-trained synthesis will extend the pipeline through a provider-neutral
`SynthesizerAdapter`, a versioned statistical profile, and a quality gate. It
must not be embedded directly in API routes or product-name branches.

```mermaid
flowchart LR
    Source[Approved source or scenario contract] --> Profile[Versioned statistical profile]
    Profile --> Intent[Reviewed quality intent]
    Intent --> Selector[Candidate selector]
    Selector --> Baseline[Deterministic and statistical baselines]
    Selector --> Optional[Optional mixture and neural adapters]
    Baseline --> Evaluation[Holdout quality evaluation]
    Optional --> Evaluation
    Evaluation --> Gate{Quality, privacy, and cost gates}
    Gate -->|pass| Runtime[Sampling runtime]
    Gate -->|fail| Rejected[Rejected candidate]
    Runtime --> Generator[Constraint and export pipeline]
```

Scenario-faithful mode does not require source rows or model fitting.
Source-faithful mode requires train, validation, and untouched holdout data plus
complete model and report lineage. The full design is maintained in
[Statistical and ML Synthesis Architecture](statistical-synthesis-architecture.md),
with gates and datasets in
[Quality Evaluation and Benchmarks](quality-evaluation-and-benchmarks.md).

### Implemented ML Worker Boundary

The first source-trained implementation is a local worker CLI, not a FastAPI
route. This preserves the service startup and deterministic product path when
the optional neural stack is absent.

```mermaid
flowchart LR
    CSV[Approved local CSV] --> Split[Deterministic split service]
    Split --> Train[Training partition]
    Split --> Validation[Validation partition]
    Split --> Holdout[Untouched holdout partition]
    Contract[Reviewed non-sensitive column contract] --> Worker[databoom-ml worker]
    Train --> Worker
    Worker --> Empirical[Owned empirical adapter]
    Worker --> GMM[Optional lazy scikit-learn mixture]
    Worker --> TensorFlow[Owned optional TensorFlow GAN]
    Worker --> CTGAN[Optional lazy CTGAN provider]
    Empirical --> Models[Checksummed local model artifacts]
    GMM --> Models
    TensorFlow --> Models
    CTGAN --> Models
    Models --> Samples[Fixed-seed candidate samples]
    Samples --> Evaluate[Dependency-light evaluator]
    Holdout --> Evaluate
    Train --> ExactCopy[Exact training-row diagnostic]
    ExactCopy --> Evaluate
    Evaluate --> Report[Experimental tournament report]
    Report --> Human[Human review and next experiment]
    API[FastAPI web process] -. no training imports .-> Worker
```

The dataset contract defaults every column to `restricted`. An operator must
explicitly classify a feature as `non_sensitive` before the experimental worker
accepts it. This is a conservative temporary policy while Masker-Boom and the
full privacy attack suite are incomplete.

Model and experiment files remain under an explicit local artifact root. The
worker records model checksum, dependency versions, provider license,
transformations, seed, and timings. The empirical and scikit-learn candidates
store data-only JSON; the TensorFlow candidate stores a Keras v3 generator and
loads it in safe mode without custom objects. CTGAN model files are Python
pickles and are therefore treated as executable local artifacts: path
containment and checksum verification are required before loading, and no
arbitrary upload/load API exists.

The local CLI is process separation, not production sandboxing. A later worker
service must add a separate image, identity, resource limits, queue, cancellation,
signed lineage, durable storage, and restricted filesystem/network access. The
research and provider decisions are detailed in
[Neural Synthesis Research](neural-synthesis-research.md).

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
