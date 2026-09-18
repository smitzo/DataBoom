# Local Development And Verification

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

## Experimental Statistical And Neural Worker

The normal installation includes the contracts, deterministic splitter,
empirical baseline, evaluator, and tournament. It does not install or import
scikit-learn, TensorFlow, pandas, torch, or CTGAN in FastAPI.

Inspect current provider availability:

```bash
.venv/bin/python -m databoom.synthesis.cli capabilities
```

Create deterministic partitions. Use `--group-column` for a subject, account,
device, patient, or another identifier whose rows must not leak across training,
validation, and holdout:

```bash
.venv/bin/python -m databoom.synthesis.cli split source.csv \
  --output-dir artifacts/ml/split \
  --group-column customer_id \
  --seed split-1
```

The output directory contains:

- `training.csv`
- `validation.csv`
- `holdout.csv`
- `split-manifest.json`

The manifest records the source checksum, algorithm, ratios, seed, grouping,
row counts, artifact paths, and partition checksums. Tournament startup verifies
those files before fitting.

Create a reviewed `DatasetContract` JSON before training. Columns default to
`restricted`; the current experimental worker accepts only columns explicitly
marked `non_sensitive`. This is intentionally conservative while the complete
privacy program is unfinished.

Create a standalone Profile v2 artifact when inspecting a reviewed source before
training:

```bash
.venv/bin/python -m databoom.synthesis.cli profile \
  source.csv \
  dataset-contract.json \
  --output-dir artifacts/ml/source-profile \
  --sample-row-limit 10000 \
  --seed profile-1
```

`profile-v2.json` contains exact source fingerprints, row counts, and null counts
plus distribution and dependency evidence from a deterministic bounded sample.
`profile-manifest.json` records its relative path and checksum. Re-running without
`--overwrite` fails instead of silently replacing evidence.

Run the owned empirical baseline:

```bash
.venv/bin/python -m databoom.synthesis.cli tournament \
  artifacts/ml/split/split-manifest.json \
  dataset-contract.json \
  --experiment-root artifacts/ml/empirical-experiment \
  --candidate empirical-independent \
  --sample-rows 10000
```

Install the optional scikit-learn Gaussian-mixture baseline when a classical
joint candidate is needed:

```bash
.venv/bin/python -m pip install -e '.[dev,ml-sklearn]'
```

Install the owned optional TensorFlow GAN only in a dedicated experiment worker:

```bash
.venv/bin/python -m pip install -e '.[dev,neural-tensorflow]'
```

Install the optional CTGAN provider only after dependency-license and source
policy review:

```bash
.venv/bin/python -m pip install torch \
  --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -e '.[dev,neural-ctgan]'
```

The explicit CPU-wheel step prevents PyPI's default Linux PyTorch resolution
from downloading an unused CUDA runtime for this CPU-declared adapter. A future
dedicated GPU worker image should own its CUDA/PyTorch matrix explicitly.

Run any installed candidates with the same experiment settings:

```bash
.venv/bin/python -m databoom.synthesis.cli tournament \
  artifacts/ml/split/split-manifest.json \
  dataset-contract.json \
  --experiment-root artifacts/ml/all-candidates-experiment \
  --candidate empirical-independent \
  --candidate sklearn-gaussian-mixture \
  --candidate tensorflow-gan \
  --candidate ctgan \
  --gmm-components 5 \
  --tensorflow-epochs 100 \
  --ctgan-epochs 300 \
  --sample-rows 10000
```

The worker writes shared training and holdout Profile v2 artifacts, per-candidate
model manifests, samples, repeat samples, synthetic profiles, quality reports,
and `tournament-report.json`. Every current decision is experimental; the report
keeps `release_approved=false` even when implemented gates pass.

Security rules:

- run only on approved local CSVs and reviewed non-sensitive columns,
- protect model directories as source-derived data,
- load TensorFlow generators only from the checksummed experiment root in safe
  mode without custom objects,
- never load an arbitrary CTGAN pickle,
- do not expose the worker as a public training endpoint,
- do not interpret an exact-match pass as formal privacy.

For the paper basis, provider license, missing-value transformation, metric
limits, and production gaps, read
[Neural Synthesis Research](../engineering/neural-synthesis-research.md).

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

Use `--domain financial` for banking-style values or `--domain healthcare` for patient-style values.

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

Open `http://localhost:3000`. Register a new account, or use the local seeded email `operator@databoom.local` with password `databoom-local`.

The dashboard can:

- show the product catalog,
- subscribe the authenticated user to a product,
- generate data through the backend product-run endpoint,
- test PostgreSQL source connections,
- save workspace sources,
- refresh relational schema metadata from a live source,
- profile source tables for row counts, null rates, cardinality, ranges, and top values,
- preview the top 20 rows for generated CSV-backed tables,
- preview MongoDB-style JSON documents for Docu-Boom runs,
- download generated artifacts and validation files.

In the Dockerized stack, users, sessions, subscriptions, workspace sources, source profiles, and generation-run metadata are persisted in PostgreSQL. Generated datasets are still written to local disk under `artifacts/`, which keeps Phase 1/2 storage simple and inspectable.

## Live PostgreSQL Introspection

Phase 2 adds backend helpers for reading schema metadata from a live PostgreSQL database through SQLAlchemy:

```python
from databoom.ingest import load_postgres_schema

schema = load_postgres_schema("postgresql+psycopg://user:password@localhost:5432/app")
```

The schema helper returns the same normalized `DatabaseSchema` used by the DDL parser, planner, generator, and validator. The API also exposes source connection testing, persisted source definitions, schema refresh, and source profiling so the dashboard can drive a full source-to-generation workflow.

## Demo Datasets

This repository includes generated CSV demos under `demo/`:

- `demo/financial-relational/csv`
- `demo/healthcare-relational/csv`

These are generated through the CLI from the schemas in each demo folder.

The command exits with code `1` if validation fails.

## Benchmarks

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

Run the Phase 2 500k-record benchmark:

```bash
.venv/bin/python benchmarks/phase2_500k.py --overwrite
```

The benchmark writes generated artifacts under:

```text
artifacts/benchmarks/phase2_500k
```

It also writes:

```text
artifacts/benchmarks/phase2_500k/metrics.json
```

Current baseline from this environment:

- 500,000 records
- 5 tables
- 233.707 seconds total
- 222.365 seconds export time
- 11.32 seconds validation time
- 52.811 MB peak memory
- 35.96 MB artifact size
- validation passed

Smoke-test the 1M five-table relational benchmark shape with scaled row counts:

```bash
.venv/bin/python benchmarks/relational_1m.py --scale 0.001 --overwrite
```

Run the full 1M five-table relational benchmark:

```bash
.venv/bin/python benchmarks/relational_1m.py --overwrite
```

The benchmark writes generated artifacts under:

```text
artifacts/benchmarks/relational_1m
```

It also writes:

```text
artifacts/benchmarks/relational_1m/metrics.json
```

Smoke-test the 1M composite-key relational benchmark shape with scaled row counts:

```bash
.venv/bin/python benchmarks/composite_keys_1m.py --scale 0.001 --overwrite
```

Run the full 1M composite-key relational benchmark:

```bash
.venv/bin/python benchmarks/composite_keys_1m.py --overwrite
```

The benchmark writes generated artifacts under:

```text
artifacts/benchmarks/composite_keys_1m
```

It also writes:

```text
artifacts/benchmarks/composite_keys_1m/metrics.json
```

Use `--skip-validation` only for export-only experiments. Official benchmark numbers should keep validation enabled.

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
