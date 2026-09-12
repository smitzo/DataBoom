# Phase 3 Graph-Boom Plan

Phase 3 begins after the Phase 2 local full-stack MVP. The phase goal is to make
DataBoom handle relationship-heavy graph data as a first-class data surface while
keeping Table-Boom and Docu-Boom stable.

## Phase 3 Status

Phase 3 is active.

The first implementation slice is backend-first:

- define graph model contracts,
- generate deterministic nodes and edges,
- export graph artifacts,
- validate edge references and cardinality,
- expose Graph-Boom through product run APIs,
- add dashboard preview support after the backend contract is stable.

LLM-assisted planning remains part of Phase 3, but it should sit behind an
interface and deterministic fallback. Graph generation must not depend on LLM
availability.

## Graph-Boom Objective

Graph-Boom generates connected datasets for systems where the core data shape is
not a table hierarchy or document tree. Examples include fraud networks,
recommendation graphs, account ownership, user-device-login graphs, claims
networks, knowledge graphs, and lineage maps.

The product should generate:

- node sets with labels and properties,
- edge sets with source and target labels,
- deterministic source and target IDs,
- configurable edge counts or fanout,
- JSON graph export for app previews,
- CSV node and edge exports for import into graph tools,
- validation reports for dangling edges, duplicate IDs, and row-count mismatches.

## Backend Design Rules

- Do not force graphs through relational table plans.
- Keep graph specs declarative and serializable.
- Reuse `SeedManager`, artifact root conventions, API run metadata, async
  progress, artifact listing, and state storage.
- Keep graph validation separate from generation.
- Treat graph output as generated artifacts first, with database-specific exports
  such as Cypher added later.
- Use source/demo resources as graph specs, not product-name conditionals.

## Phase 3 Implementation Steps

1. Add `databoom.graph.models` with node, edge, property, artifact, manifest,
   validation, and result contracts.
2. Add `databoom.graph.generator` with deterministic node and edge generation.
3. Add Graph-Boom catalog defaults and make the product active.
4. Wire `DataProductKind.GRAPH` into product run execution and async placeholders.
5. Add a graph preview API endpoint for top nodes and edges.
6. Add tests for generation, validation, artifacts, API product flow, and preview.
7. Add frontend graph workspace rendering after the backend surface is proven.
8. Add planner abstractions for structured run plans and optional LLM assistance.

## Done Criteria For First Phase 3 Slice

- Graph-Boom appears as an active product.
- A subscribed user can run Graph-Boom from the product API.
- The run writes graph JSON, node CSV, edge CSV, manifest, and validation files.
- Validation rejects dangling edge references.
- Async progress reports generated graph records.
- Artifact downloads work through the existing run artifact endpoint.
- A preview endpoint returns top nodes and edges.
- Backend tests cover the new graph path.
