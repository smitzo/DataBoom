# Phase 1 Usage

This guide covers the current Phase 1 backend workflow: parse PostgreSQL DDL, create a deterministic plan, generate rows, export CSV/SQL artifacts, and validate the result.

## Local Setup

Create and install the Python 3.12 virtual environment:

```bash
/home/odoo/.local/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Run checks:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

## Generate Data

Create a schema file:

```sql
CREATE TABLE accounts (
    id bigint PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE users (
    id bigint PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES accounts(id),
    email text NOT NULL
);
```

Run generation:

```bash
.venv/bin/databoom generate schema.sql \
  --output-dir artifacts/demo \
  --rows accounts=10 \
  --rows users=50 \
  --format csv \
  --format sql \
  --domain general \
  --seed demo
```

Preview the deterministic plan without writing artifacts:

```bash
.venv/bin/databoom plan schema.sql \
  --rows accounts=10 \
  --rows users=50 \
  --format csv \
  --seed demo
```

Re-validate an existing artifact directory:

```bash
.venv/bin/databoom validate schema.sql artifacts/demo \
  --rows accounts=10 \
  --rows users=50 \
  --format csv \
  --format sql \
  --seed demo
```

Expected outputs:

- `artifacts/demo/manifest.json`
- `artifacts/demo/validation.json`
- one CSV file per table
- one JSON file per table when `--format json` is used
- one SQL file per table when `--format sql` is used

Use `--domain financial` for Bank-O-Boom values or `--domain healthcare` for Health-Boom values.

## API Artifacts

API runs can be created with `POST /runs`, inspected with `GET /runs/{run_id}`, and their generated files can be listed or downloaded with:

```text
GET /runs/{run_id}/artifacts
GET /runs/{run_id}/artifacts/{relative_artifact_path}
```

When `DATABOOM_API_KEY` is configured, include `X-API-Key` on run and artifact requests. Health and readiness endpoints remain open for local orchestration checks.

## Full-Stack Local Run

When the Dockerized backend uses alternate host ports, start the API stack with:

```bash
DATABOOM_API_PORT=8001 DATABOOM_POSTGRES_PORT=55432 DATABOOM_REDIS_PORT=56379 docker compose up -d --build
```

Then start the frontend against that API:

```bash
cd frontend
NEXT_PUBLIC_DATABOOM_API_URL=http://localhost:8001 npm run dev -- --hostname 0.0.0.0 --port 3000
```

Open `http://localhost:3000`. Login with email `demo` and password `demo`.

The dashboard can:

- show the product catalog,
- subscribe the demo user to a product,
- generate data through the backend product-run endpoint,
- preview the top 10 rows for generated CSV-backed tables,
- download generated table artifacts and validation files.

In the Dockerized stack, demo sessions, subscriptions, and generation-run metadata are persisted in PostgreSQL. Generated datasets are still written to local disk under `artifacts/`, which keeps Phase 1/2 storage simple and inspectable.

## Live PostgreSQL Introspection

Phase 2 adds a backend ingestion helper for reading schema metadata from a live PostgreSQL database through SQLAlchemy:

```python
from databoom.ingest import load_postgres_schema

schema = load_postgres_schema("postgresql+psycopg://user:password@localhost:5432/app")
```

The helper returns the same normalized `DatabaseSchema` used by the DDL parser, planner, generator, and validator.

## Demo Datasets

This repository includes generated CSV demos under `demo/`:

- `demo/bank-o-boom/csv`
- `demo/health-boom/csv`

These are generated through the CLI from the schemas in each demo folder.

The command exits with code `1` if validation fails.

## Benchmark

Run the Phase 1 100k-record benchmark:

```bash
.venv/bin/python benchmarks/phase1_100k.py --overwrite
```

The benchmark writes generated artifacts under:

```text
artifacts/benchmarks/phase1_100k
```

It also writes:

```text
artifacts/benchmarks/phase1_100k/metrics.json
```

Current baseline from this environment:

- 100,000 records
- 3 tables
- 44.691 seconds
- 50.71 MB peak memory
- 5.312 MB artifact size
- validation passed

## Docker Compose

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

The current Compose stack includes the FastAPI service, PostgreSQL, and Redis. Celery and Kafka are intentionally not included until a real queue or event-streaming requirement appears.
