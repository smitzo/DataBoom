# DataBoom

DataBoom is a synthetic data and masking platform for teams that need realistic, repeatable, integrity-safe datasets without casually copying production data.

## Product Family

| Product | Purpose | Status |
| --- | --- | --- |
| `Table-Boom` | Relational/table generation with key integrity and CSV/JSON/SQL exports. | Active |
| `Docu-Boom` | NoSQL document generation with nested JSON/NDJSON artifacts. | Active |
| `Graph-Boom` | Node and edge generation for graph datasets. | Active |
| `Masker-Boom` | Redaction, masking, tokenization, and integrity-preserving privacy workflows. | Planned for Phase 4 |

See [DataBoom Product Family](docs/product/product-family.md) for the canonical product taxonomy.

The current implementation includes Table-Boom relational generation, Docu-Boom document generation, Graph-Boom node/edge generation, and reviewed assisted planning with deterministic fallback. Banking, healthcare, ecommerce, SaaS, and similar domains are demo use cases or profiles, not separate products.

## Current Capabilities

- PostgreSQL DDL ingestion.
- Normalized schema models.
- Relationship-aware generation with primary-key and foreign-key preservation.
- Deterministic seeds.
- General, financial, and healthcare demo domain profiles.
- Locale-aware `en-US` and `en-IN` identity generation with correlated names,
  gender, email, phone, city, region, country, postcode, age, and birth date.
- CSV, JSON, and SQL local artifact exports.
- Validation reports and artifact manifests.
- CLI generation, plan preview, and artifact validation workflows.
- FastAPI app scaffold with health and readiness endpoints.
- API generation run endpoint for synchronous local relational runs.
- Async product-run endpoint with progress percentage, expected seconds, and operation timing telemetry.
- API artifact listing, downloads, and optional API-key protection.
- Email/password registration and login with server-side password hashes.
- Product catalog, subscription, product-run, table-preview, and document-preview API endpoints.
- Graph-Boom node/edge generation with graph JSON, nodes CSV, edges CSV, graph validation, and graph-preview API support.
- SQL-backed users, sessions, subscriptions, workspace sources, source profiles, and run metadata.
- Optional LLM-assisted plan proposals with strict output validation, prompt-cache telemetry, explicit review, approved-plan execution, and deterministic fallback.
- DataBoom workspace with product navigation, live top-20 relational table previews, NoSQL document previews, agent run steps, subscriptions, runs, and artifact downloads.
- Row-level async progress with generated-row counts, current resource, rows/sec, remaining time, and operation timings.
- Live PostgreSQL source testing, schema refresh, DDL snapshot storage, and source profiling.
- Refreshed relational sources retain schema names, column details, primary keys, foreign keys, unique constraints, and refresh timestamps.
- Cached source profiles can drive relationship fanout for source-shaped Table-Boom output.
- 100k-record Phase 1 benchmark.
- 500k-record Phase 2 benchmark baseline.
- 1M-record five-table relational benchmark harness.
- 1M-record composite-key relational benchmark harness.
- Next.js and Tailwind frontend workbench.
- Render Blueprint for the FastAPI backend, Vercel-ready frontend envs, and Supabase Postgres compatibility.

## Why DataBoom Data Is Realistic

Realistic synthetic data is not a collection of individually plausible cells. A
row can contain a believable name, phone number, and city and still be unusable
when those values contradict one another. DataBoom builds realism in layers:

1. **Schema fidelity:** generated values respect SQL types, nullability, primary
   keys, unique constraints, composite keys, foreign keys, and dependency order.
2. **Relationship fidelity:** child records reference generated parent records,
   with balanced or source-profiled fanout instead of arbitrary identifiers.
3. **Distribution fidelity:** source profiles can preserve null rates, frequent
   categories, numeric ranges, datetime ranges, and relationship fanout without
   sending source rows to an LLM.
4. **Semantic fidelity:** financial, healthcare, and general providers understand
   domain fields instead of treating every string as interchangeable text.
5. **Row-level coherence:** one locale-aware person context produces the name,
   gender, email, phone, city, state, country, postcode, age, and birth date for a
   row. An Indian profile therefore uses Indian identity and geography rules;
   a US profile uses US rules.
6. **Reproducibility and validation:** a deterministic seed recreates the run,
   while manifests and validators check the exported artifacts after generation.

DataBoom currently ships `en-US` and `en-IN` person contexts. More locales can be
added as catalog adapters without changing the row, export, or validation engine.
Known identity, geography, type, and relationship contradictions are prevented by
engine rules. For an arbitrary business schema, absolute consistency still
requires explicit constraints or learned joint profiles; DataBoom does not claim
that a plausible value automatically proves statistical equivalence to production.

## Why ChatGPT Alone Cannot Generate the Same Dataset

An LLM can draft a small sample or interpret a requirement such as “Indian retail
customers.” It is not a bulk data engine:

- printing hundreds of thousands of rows consumes output tokens on repetitive
  serialization and can exceed response limits;
- a model response has no streaming artifact writer, checkpoint, backpressure,
  or bounded-memory foreign-key registry;
- exact primary-key, foreign-key, uniqueness, count, and cross-column guarantees
  are difficult to maintain across a very long response;
- retries may change previously generated values unless a separate deterministic
  execution layer owns the seed and rules;
- prose that looks correct is not a substitute for validating CSV, SQL, JSON,
  NDJSON, or graph artifacts after they are written.

DataBoom uses an LLM only where it adds leverage: interpreting intent and proposing
a small, reviewable plan. The deterministic engine then generates, streams,
validates, previews, and exports every record. If the LLM key is missing or its
credits are exhausted, deterministic planning and generation remain available.

## Why DataBoom Is More Than Faker or a Prompt

DataBoom can use locale catalogues for primitive values such as first and last
names. That is useful, but a primitive value provider does not ingest a schema,
solve table order, preserve composite relationships, reproduce an approved plan,
stream one million records, or validate exported artifacts. DataBoom provides
that orchestration layer and keeps value providers replaceable.

The product's differentiator is therefore not a longer list of random names. It
is the combination of reviewed planning, correlated row contexts, source-aware
profiles, deterministic high-volume execution, integrity validation, and
multi-format delivery behind one reusable engine.

## Roadmap Summary

- Phase 1: Table-Boom relational foundation for PostgreSQL schema-driven generation.
- Phase 2: Table-Boom scale, FastAPI workflows, source profiling, refreshed-source generation, and Docu-Boom NoSQL document support. `complete for local full-stack MVP`
- Phase 3: Graph-Boom support, graph previews/exports, optional LLM-assisted planning, and operator-facing review flows. `complete`
- Phase 4: Masker-Boom policies, redaction, masking, hashing, tokenization, audit logs, and security hardening.
- Phase 5: production deployment hardening, CI, observability, retention, and adapter extensibility.

## Backend Setup

Use Python 3.12.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Run backend checks:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

Generate a dataset:

```bash
.venv/bin/databoom generate demo/financial-relational/schema.sql \
  --output-dir artifacts/demo-financial-relational \
  --rows customers=100 \
  --rows bank_accounts=250 \
  --rows transactions=750 \
  --format csv \
  --format json \
  --format sql \
  --domain financial \
  --locale en-IN \
  --seed demo-financial-relational
```

Preview the deterministic plan before generation:

```bash
.venv/bin/databoom plan demo/financial-relational/schema.sql \
  --rows customers=100 \
  --rows bank_accounts=250 \
  --rows transactions=750 \
  --format csv \
  --domain financial \
  --locale en-IN \
  --seed demo-financial-relational
```

Validate an existing artifact directory without regenerating it:

```bash
.venv/bin/databoom validate demo/financial-relational/schema.sql artifacts/demo-financial-relational \
  --rows customers=100 \
  --rows bank_accounts=250 \
  --rows transactions=750 \
  --format csv \
  --format json \
  --format sql \
  --domain financial \
  --locale en-IN \
  --seed demo-financial-relational
```

Run the Phase 1 benchmark:

```bash
.venv/bin/python benchmarks/phase1_100k.py --overwrite
```

Run the Phase 2 500k benchmark:

```bash
.venv/bin/python benchmarks/phase2_500k.py --overwrite
```

Smoke-test the 1M benchmark shape with scaled row counts:

```bash
.venv/bin/python benchmarks/relational_1m.py --scale 0.001 --overwrite
```

Run the full 1M relational benchmark:

```bash
.venv/bin/python benchmarks/relational_1m.py --overwrite
```

Smoke-test the 1M composite-key benchmark shape:

```bash
.venv/bin/python benchmarks/composite_keys_1m.py --scale 0.001 --overwrite
```

Run the full 1M composite-key benchmark:

```bash
.venv/bin/python benchmarks/composite_keys_1m.py --overwrite
```

Run the API locally:

```bash
.venv/bin/uvicorn databoom.api:create_app --factory --reload
```

Health checks:

```text
http://localhost:8000/health
http://localhost:8000/ready
```

Create a small API generation run:

```bash
curl -X POST http://localhost:8000/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "schema_ddl": "CREATE TABLE users (id bigint PRIMARY KEY, email text NOT NULL);",
    "row_counts": {"users": 3},
    "seed": "api-demo",
    "locale": "en-IN",
    "domain": "general",
    "output_formats": ["csv", "json"]
  }'
```

Use the returned `run_id` to inspect and download local artifacts:

```bash
curl http://localhost:8000/runs/<run_id>/artifacts
curl -L -o users.csv http://localhost:8000/runs/<run_id>/artifacts/public__users.csv
```

Set `DATABOOM_API_KEY` to require `X-API-Key` on run and artifact routes:

```bash
curl -H "X-API-Key: $DATABOOM_API_KEY" http://localhost:8000/runs
```

## Frontend Setup

```bash
cd frontend
npm install
npm run typecheck
npm run build
NEXT_PUBLIC_DATABOOM_API_URL=http://localhost:8000 npm run dev -- --hostname 0.0.0.0 --port 3000
```

Open:

```text
http://localhost:3000
```

Public routes:

- `/`: landing page with core product positioning and engine proof.
- `/products`: product catalog for Table-Boom, Docu-Boom, Graph-Boom, and Masker-Boom.
- `/demos`: demo data, use cases, output formats, and validation baseline.
- `/roadmap`: phase roadmap with achieved and future steps.
- `/contact`: evaluation checklist and implementation guidance.

Authenticated routes:

- `/login`: email/password sign-in.
- `/register`: account creation.
- `/dashboard`: product workspace.
- `/runs`: generated run history.
- `/settings`: account and LLM provider policy.
- `/settings/subscriptions`: subscription management.

For the Dockerized backend currently running on alternate local ports, start the frontend like this:

```bash
cd frontend
NEXT_PUBLIC_DATABOOM_API_URL=http://localhost:8001 npm run dev -- --hostname 0.0.0.0 --port 3000
```

Then open:

```text
http://localhost:3000
```

Register from `/register` or sign in with a configured seed account. Local and Docker environments seed `operator@databoom.local` / `databoom-local` automatically for convenience; production Render deployments should set `DATABOOM_SEED_EMAIL` and `DATABOOM_SEED_PASSWORD` only when a pre-created reviewer/admin account is needed. The dashboard can subscribe to active products, test PostgreSQL source connections, save workspace sources, refresh relational schema metadata, profile source tables, generate data through the async backend flow, show top-20 relational table previews while CSV artifacts are being written, show MongoDB-style document previews from JSON or NDJSON artifacts, display generated rows, rows/sec, expected and remaining time, operation timings, and link to downloadable artifacts.

## Deployment: Render + Supabase + Vercel

The current deployable stack is:

- Render: FastAPI engine container from `Dockerfile` and `render.yaml`.
- Supabase: hosted PostgreSQL for API state through `DATABOOM_DATABASE_URL`.
- Vercel: Next.js frontend from `frontend/`.
- Optional LLM: platform key via `DATABOOM_LLM_PLATFORM_API_KEY`, or user BYOK from `/settings`.

Deployment guide: [docs/operations/deployment.md](docs/operations/deployment.md).

Minimum production environment variables:

```text
# Render API
DATABOOM_DATABASE_URL=<supabase pooled or direct connection string>
DATABOOM_CORS_ORIGINS=https://<your-vercel-app>.vercel.app,http://localhost:3000
DATABOOM_ALLOW_REGISTRATION=true

# Vercel frontend
NEXT_PUBLIC_DATABOOM_API_URL=https://<your-render-api>.onrender.com
```

## Docker

Validate Compose configuration:

```bash
docker compose --profile tools config
```

Start the Dockerized API stack when Docker daemon is available:

```bash
docker compose up -d --build
```

The API should be available at:

```text
http://localhost:8000/health
```

If a local service already uses the default API, PostgreSQL, or Redis ports, choose alternate host ports:

```bash
DATABOOM_API_PORT=8001 DATABOOM_POSTGRES_PORT=55432 DATABOOM_REDIS_PORT=56379 docker compose up -d --build
```

Run the CLI image as a tool container:

```bash
docker compose --profile tools run --rm app
```

## Folder Guide

- `src/databoom`: Python backend package.
- `src/databoom/api`: FastAPI app factory, response models, HTTP routes, product catalog, and API state storage.
- `src/databoom/ingest`: PostgreSQL DDL ingestion.
- `src/databoom/profiling`: source connection testing and PostgreSQL table profiling.
- `src/databoom/schema`: normalized schema models and relationship graph code.
- `src/databoom/generation`: plans, seeds, domain profiles, row generation, and values.
- `src/databoom/graph`: Graph-Boom node/edge contracts, deterministic graph generator, graph artifacts, and graph validation.
- `src/databoom/planning`: planner contracts, deterministic and hosted adapters, versioned prompt packs, cache telemetry, and proposal validation.
- `src/databoom/synthesis`: source-trained split contracts, provider-neutral
  adapters, empirical, scikit-learn mixture, owned TensorFlow GAN, and CTGAN
  candidates, quality evaluation, and the isolated ML worker CLI.
- `src/databoom/export`: local artifact writers.
- `src/databoom/validation`: validation report logic.
- `tests`: backend test suite.
- `benchmarks`: repeatable benchmark scripts.
- `demo`: checked-in financial and healthcare CSV demo datasets plus schemas.
- `frontend`: Next.js, TypeScript, Tailwind frontend workbench.
- `frontend/src/components`: reusable frontend UI components.
- `frontend/src/data`: shared frontend display data, including roadmap entries.
- `docs`: product, engineering, and operations documentation.
- `openspec`: active task requirements/designs and archived completed changes.

## Docs Guide

- `docs/README.md`: documentation index and separation of concerns.
- `docs/product/product-family.md`: DataBoom platform products and use-case naming rules.
- `docs/product/functional-specification.md`: product behavior, users, workflows, and acceptance criteria.
- `docs/product/product-reasoning-faq.md`: 4W1H reasoning and competitive/product FAQ.
- `docs/product/design-research.md`: product and workflow lessons from adjacent synthetic-data tools.
- `docs/engineering/high-level-design.md`: system boundaries, planning review, extensibility, API flow, frontend routes, and deployment topology.
- `docs/engineering/low-level-design.md`: Python modules, contracts, execution sequences, state, artifacts, and failure boundaries.
- `docs/engineering/engineering-standards.md`: reusable backend/frontend code standards.
- `docs/engineering/roadmap.md`: phase status, objectives, and commit sequence.
- `docs/engineering/optimization-plan.md`: optimization roadmap for engine speed, quality, profiling, blueprints, and observability.
- `docs/engineering/statistical-synthesis-architecture.md`: scenario/source modes, statistical profiles, model portfolio, selection policy, and ML delivery stages.
- `docs/engineering/quality-evaluation-and-benchmarks.md`: fidelity, utility, privacy, benchmark datasets, experiment procedure, and release gates.
- `docs/engineering/neural-synthesis-research.md`: primary GAN research,
  classical and neural candidate roles, provider licensing, worker isolation,
  evaluation, and remaining release gates.
- `docs/engineering/frontend-development.md`: frontend design principles and phased UI plan.
- `docs/engineering/prompt-caching-and-instructions.md`: prompt caching and Codex/OpenAI instruction strategy.
- `docs/operations/local-development.md`: backend/frontend setup, CLI, benchmarks, demos, and Docker usage.
- `docs/operations/phase-history`: completed phase handoffs and verification evidence.
- `docs/operations/deployment.md`: Render, Supabase, Vercel, and LLM key policy deployment guide.
- `AGENTS.md`: operating rules for coding agents working in this repo.
- `openspec/changes`: active OpenSpec proposals, requirements, designs, and task ledgers.
- `openspec/changes/archive`: completed implementation specifications and evidence.
- `understanding.md`: explanation log for significant decisions.
