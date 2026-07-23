# DataBoom

DataBoom is a synthetic data engine for generating realistic, repeatable datasets from schemas, prompts, and future data-family specifications.

The current implementation is Phase 1: a Python backend engine that reads PostgreSQL DDL, plans dependency-aware relational generation, writes local CSV/JSON/SQL artifacts, and produces validation reports. The frontend is a Next.js workbench that presents the product, current benchmark status, domain profiles, roadmap, and demo datasets.

## Current Capabilities

- PostgreSQL DDL ingestion.
- Normalized schema models.
- Relationship-aware generation with primary-key and foreign-key preservation.
- Deterministic seeds.
- Financial, healthcare, and general domain profiles.
- CSV, JSON, and SQL local artifact exports.
- Validation reports and artifact manifests.
- CLI generation, plan preview, and artifact validation workflows.
- FastAPI app scaffold with health and readiness endpoints.
- API generation run endpoint for synchronous local relational runs.
- API artifact listing, downloads, and optional API-key protection.
- Live PostgreSQL schema introspection foundation.
- 100k-record Phase 1 benchmark.
- Next.js and Tailwind frontend workbench.

## Roadmap Summary

- Phase 1: relational backend foundation for PostgreSQL schema-driven generation.
- Phase 2: scale toward 500k records, add FastAPI workflows, profiling, and NoSQL document data support.
- Phase 3: add LLM-assisted planning, graph data support, and richer operator-facing review flows.
- Phase 4: add privacy policies, masking, hashing, tokenization, audit logs, and security hardening.
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
.venv/bin/databoom generate demo/financial/schema.sql \
  --output-dir artifacts/demo-financial \
  --rows customers=100 \
  --rows bank_accounts=250 \
  --rows transactions=750 \
  --format csv \
  --format json \
  --format sql \
  --domain financial \
  --seed demo-financial
```

Preview the deterministic plan before generation:

```bash
.venv/bin/databoom plan demo/financial/schema.sql \
  --rows customers=100 \
  --rows bank_accounts=250 \
  --rows transactions=750 \
  --format csv \
  --domain financial \
  --seed demo-financial
```

Validate an existing artifact directory without regenerating it:

```bash
.venv/bin/databoom validate demo/financial/schema.sql artifacts/demo-financial \
  --rows customers=100 \
  --rows bank_accounts=250 \
  --rows transactions=750 \
  --format csv \
  --format json \
  --format sql \
  --domain financial \
  --seed demo-financial
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

## Docker

Validate Compose configuration:

```bash
docker compose --profile tools config
```

Start local infrastructure when Docker daemon is available:

```bash
docker compose up -d postgres redis
```

Run the app tool container:

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
- `demo`: checked-in financial and healthcare CSV demo datasets plus schemas.
- `frontend`: Next.js, TypeScript, Tailwind frontend workbench.
- `frontend/src/components`: reusable frontend UI components.
- `frontend/src/data`: shared frontend display data, including roadmap entries.
- `docs`: product, technical, roadmap, usage, prompt, reasoning, and frontend planning documents.

## Docs Guide

- `instructions.md`: project entrypoint and commit discipline.
- `docs/functional-specification.md`: product behavior, users, workflows, and acceptance criteria.
- `docs/technical-design-and-roadmap.md`: system design, phase roadmap, objectives, and commit sequence.
- `docs/frontend-development.md`: frontend design principles and phased UI plan.
- `docs/phase1-usage.md`: current backend setup, CLI, benchmark, and Docker usage.
- `docs/product-reasoning-faq.md`: 4W1H reasoning and competitive/product FAQ.
- `docs/prompt-caching-and-instructions.md`: prompt caching and Codex/OpenAI instruction strategy.
- `docs/synthetic-data-inspiration.md`: lessons from Tonic.ai, Gretel Synthetics, and generatedata.com.
- `AGENTS.md`: operating rules for coding agents working in this repo.
- `understanding.md`: explanation log for significant decisions.
