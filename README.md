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
- `src/databoom/export`: local artifact writers.
- `src/databoom/validation`: validation report logic.
- `tests`: backend test suite.
- `benchmarks`: repeatable benchmark scripts.
- `demo`: checked-in financial and healthcare CSV demo datasets plus schemas.
- `frontend`: Next.js, TypeScript, Tailwind frontend workbench.
- `frontend/src/components`: reusable frontend UI components.
- `frontend/src/data`: shared frontend display data, including roadmap entries.
- `docs`: product, engineering, and operations documentation.

## Docs Guide

- `instructions.md`: project entrypoint and commit discipline.
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
- `docs/engineering/frontend-development.md`: frontend design principles and phased UI plan.
- `docs/engineering/prompt-caching-and-instructions.md`: prompt caching and Codex/OpenAI instruction strategy.
- `docs/operations/local-development.md`: backend/frontend setup, CLI, benchmarks, demos, and Docker usage.
- `docs/operations/phase-history`: completed phase handoffs and verification evidence.
- `docs/operations/deployment.md`: Render, Supabase, Vercel, and LLM key policy deployment guide.
- `AGENTS.md`: operating rules for coding agents working in this repo.
- `understanding.md`: explanation log for significant decisions.
