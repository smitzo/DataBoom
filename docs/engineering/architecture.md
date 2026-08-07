# DataBoom Architecture

DataBoom is designed as a product platform, not a single hard-coded generator. The extension point is the data surface: relational tables, document collections, graph nodes/edges, and masking policies.

## System Context

```mermaid
flowchart LR
    Visitor[Public website visitor] --> PublicSite[Next.js public site]
    Operator[Authenticated demo operator] --> Dashboard[Next.js dashboard]
    Developer[Developer or CI] --> CLI[Typer CLI]

    PublicSite --> Login[Demo login]
    Login --> Dashboard
    Dashboard --> API[FastAPI API]
    CLI --> Engine[DataBoom engine]
    API --> Engine

    API --> StateStore[StateStore boundary]
    StateStore --> MetadataDB[(PostgreSQL metadata)]
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
    Kind -->|graph| GraphBoom[Graph-Boom planned]
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
flowchart LR
    Request[Generation request] --> ProductResolver[Resolve product/catalog config]
    ProductResolver --> Planner[Plan builder]

    subgraph RelationalPath[Relational path]
        DDL[DDL or live schema] --> SchemaIngestor[Schema ingestor]
        SchemaIngestor --> RelationshipGraph[Relationship graph]
        RelationshipGraph --> RelationalPlan[Relational generation plan]
    end

    subgraph DocumentPath[Document path]
        DocumentSpec[Document collection specs] --> DocumentPlan[Document generation plan]
    end

    Planner --> RelationalPlan
    Planner --> DocumentPlan
    RelationalPlan --> SeedManager[Deterministic seed manager]
    DocumentPlan --> SeedManager
    SeedManager --> Runtime[Run context]
    Runtime --> Generator[Generator]
    Generator --> Exporter[Artifact exporter]
    Exporter --> Validator[Validator]
    Validator --> Manifest[Manifest and validation report]
```

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
    participant Catalog as Product catalog
    participant Engine as Generation engine
    participant Store as StateStore
    participant Disk as Local artifacts

    UI->>API: POST /auth/login
    API->>Store: save demo session
    UI->>API: POST /subscriptions
    API->>Catalog: validate product and plan
    API->>Store: save subscription
    UI->>API: POST /products/{product_id}/runs
    API->>Store: verify subscription
    API->>Catalog: resolve product kind and defaults
    API->>Engine: execute product generation
    Engine->>Disk: write artifacts, manifest, validation
    API->>Store: save run metadata
    API-->>UI: run response
    UI->>API: GET preview/artifacts
    API-->>UI: top records and download links
```

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
    Dashboard --> Settings[/settings/subscriptions authenticated settings]

    Dashboard --> DataWorkspace[DataWorkspace component]
    DataWorkspace --> RelationalSurface[Table grid for relational products]
    DataWorkspace --> DocumentSurface[JSON cards for document products]
    DataWorkspace --> PlannedSurface[Planned state for graph/masking]
```

The public pages should contain core product marketing and knowledge. The authenticated routes should contain operational workflow: subscribe, generate, preview, download, and inspect runs.

## Deployment Topology

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

Current local deployment uses Docker Compose for FastAPI, PostgreSQL, and Redis. Next.js runs as the local frontend during development. Phase 5 should add a production frontend container, CI, structured logging, retention controls, and deployment documentation.

## How To Add A New Product Kind

1. Add or extend the product kind enum and API response contract.
2. Add a catalog entry with defaults, output formats, status, features, and use cases.
3. Add an internal spec/model for the new data surface.
4. Add a generator service that returns the shared run response shape.
5. Add validation and artifact export logic for that surface.
6. Add preview endpoints when the data shape needs a custom preview.
7. Add a frontend surface component selected by `product.kind`.
8. Add focused tests for catalog, generation, preview, artifact, and planned-state behavior.

This sequence keeps the platform extendable without scattering product-name conditionals across routes or UI pages.
