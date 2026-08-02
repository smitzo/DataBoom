# DataBoom

DataBoom is a synthetic data and masking platform for teams that need realistic, repeatable, integrity-safe datasets without casually copying production data.

## Product Family

| Product | Purpose | Status |
| --- | --- | --- |
| `Generator-Boom` | Synthetic data generation from schemas, prompts, domain profiles, and future document/graph specs. | Active |
| `Masker-Boom` | Redaction, masking, tokenization, and integrity-preserving privacy workflows for sensitive source data. | Planned for Phase 4 |

Generator-Boom contains whacky but useful modules:

| Module | Purpose | Status |
| --- | --- | --- |
| `Schema-Boom` | PostgreSQL-first schema-aware relational generation. | Active |
| `Bank-O-Boom` | Banking and fintech demo/profile generation. | Active demo |
| `Health-Boom` | Medical and patient-style demo/profile generation. | Active demo |
| `Boom-Commerce` | Ecommerce, orders, payments, refunds, and inventory data. | Planned |
| `Auto-Boom` | Automotive, fleet, insurance, and service datasets. | Planned |
| `Docu-Boom` | NoSQL document and nested JSON generation. | Phase 2 planned |
| `Graph-Boom` | Node and edge generation for graph datasets. | Phase 3 planned |

See [DataBoom Product Family](docs/product-family.md) for the canonical product taxonomy.

The current implementation is Generator-Boom: a Python backend engine that reads PostgreSQL DDL, plans dependency-aware relational generation, writes local CSV/JSON/SQL artifacts, and produces validation reports. The frontend is a Next.js workbench that presents the product, current benchmark status, domain profiles, roadmap, and demo datasets.

## Current Capabilities

- PostgreSQL DDL ingestion.
- Normalized schema models.
- Relationship-aware generation with primary-key and foreign-key preservation.
- Deterministic seeds.
- Bank-O-Boom, Health-Boom, and general domain profiles.
- CSV, JSON, and SQL local artifact exports.
- Validation reports and artifact manifests.
- CLI generation, plan preview, and artifact validation workflows.
- FastAPI app scaffold with health and readiness endpoints.
- API generation run endpoint for synchronous local relational runs.
- API artifact listing, downloads, and optional API-key protection.
- Frontend API bridge for health checks, generation runs, generated table output, and artifact downloads.
- Live PostgreSQL schema introspection foundation.
- 100k-record Phase 1 benchmark.
- Next.js and Tailwind frontend workbench.

## Roadmap Summary

- Phase 1: Generator-Boom Schema-Boom relational foundation for PostgreSQL schema-driven generation.
- Phase 2: Generator-Boom scale, FastAPI workflows, profiling, and Docu-Boom NoSQL document support.
- Phase 3: Generator-Boom LLM-assisted planning, Graph-Boom support, and richer operator-facing review flows.
- Phase 4: Masker-Boom policies, redaction, masking, hashing, tokenization, audit logs, and security hardening.
- Phase 5: production deployment, CI, observability, retention, and adapter extensibility.

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
.venv/bin/databoom generate demo/bank-o-boom/schema.sql \
  --output-dir artifacts/demo-bank-o-boom \
  --rows customers=100 \
  --rows bank_accounts=250 \
  --rows transactions=750 \
  --format csv \
  --format json \
  --format sql \
  --domain financial \
  --seed demo-bank-o-boom
```

Preview the deterministic plan before generation:

```bash
.venv/bin/databoom plan demo/bank-o-boom/schema.sql \
  --rows customers=100 \
  --rows bank_accounts=250 \
  --rows transactions=750 \
  --format csv \
  --domain financial \
  --seed demo-bank-o-boom
```

Validate an existing artifact directory without regenerating it:

```bash
.venv/bin/databoom validate demo/bank-o-boom/schema.sql artifacts/demo-bank-o-boom \
  --rows customers=100 \
  --rows bank_accounts=250 \
  --rows transactions=750 \
  --format csv \
  --format json \
  --format sql \
  --domain financial \
  --seed demo-bank-o-boom
```

Run the Phase 1 benchmark:

```bash
.venv/bin/python benchmarks/phase1_100k.py --overwrite
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

For the Dockerized backend currently running on alternate local ports, start the frontend like this:

```bash
cd frontend
NEXT_PUBLIC_DATABOOM_API_URL=http://localhost:8001 npm run dev -- --hostname 0.0.0.0 --port 3001
```

Then open:

```text
http://localhost:3001
```

The hero control center can call the backend, create a small generation run, show generated tables, and link to downloadable CSV/JSON artifacts.

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
- `src/databoom/api`: FastAPI app factory, response models, and HTTP routes.
- `src/databoom/ingest`: PostgreSQL DDL ingestion.
- `src/databoom/schema`: normalized schema models and relationship graph code.
- `src/databoom/generation`: plans, seeds, domain profiles, row generation, and values.
- `src/databoom/export`: local artifact writers.
- `src/databoom/validation`: validation report logic.
- `tests`: backend test suite.
- `benchmarks`: repeatable benchmark scripts.
- `demo`: checked-in Bank-O-Boom and Health-Boom CSV demo datasets plus schemas.
- `frontend`: Next.js, TypeScript, Tailwind frontend workbench.
- `frontend/src/components`: reusable frontend UI components.
- `frontend/src/data`: shared frontend display data, including roadmap entries.
- `docs`: product, technical, roadmap, usage, prompt, reasoning, and frontend planning documents.

## Docs Guide

- `instructions.md`: project entrypoint and commit discipline.
- `docs/product-family.md`: DataBoom platform, Generator-Boom modules, and Masker-Boom modules.
- `docs/functional-specification.md`: product behavior, users, workflows, and acceptance criteria.
- `docs/technical-design-and-roadmap.md`: system design, phase roadmap, objectives, and commit sequence.
- `docs/frontend-development.md`: frontend design principles and phased UI plan.
- `docs/phase1-usage.md`: current backend setup, CLI, benchmark, and Docker usage.
- `docs/product-reasoning-faq.md`: 4W1H reasoning and competitive/product FAQ.
- `docs/prompt-caching-and-instructions.md`: prompt caching and Codex/OpenAI instruction strategy.
- `docs/synthetic-data-inspiration.md`: lessons from Tonic.ai, Gretel Synthetics, and generatedata.com.
- `AGENTS.md`: operating rules for coding agents working in this repo.
- `understanding.md`: explanation log for significant decisions.
