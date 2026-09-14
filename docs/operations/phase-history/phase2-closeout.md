# Phase 2 Closeout

This document freezes what Phase 2 means for DataBoom and defines the handoff into
Phase 3. It is intentionally operations-focused: a reviewer should be able to run
the product, log in, generate data, preview it, and download artifacts.

## Phase 2 Status

Phase 2 is complete for the local full-stack MVP.

The completed surface includes:

- Table-Boom relational generation from demo schemas and refreshed PostgreSQL source metadata.
- Docu-Boom document generation with JSON and NDJSON artifacts.
- Email/password auth with server-side password hashes.
- Seeded local operator account for development and review.
- Product subscriptions for Table-Boom and Docu-Boom.
- Async product runs with progress, generated-row counts, rows/sec, ETA, and operation timings.
- Top-row relational previews and MongoDB-style document previews.
- Artifact listing and download support.
- SQL-backed API state for users, sessions, subscriptions, workspace sources, source profiles, and run metadata.
- Source connection testing, schema refresh, and source profiling.
- Local disk artifacts for Phase 1 and Phase 2.
- Render, Supabase, and Vercel deployment guide.
- Frontend public pages, demos, login/register, dashboard, runs, settings, and product workspaces.

## Local Login

Start the backend:

```bash
.venv/bin/uvicorn databoom.api:create_app --factory --reload --host 0.0.0.0 --port 8000
```

Start the frontend:

```bash
cd frontend
NEXT_PUBLIC_DATABOOM_API_URL=http://localhost:8000 npm run dev -- --hostname 0.0.0.0 --port 3000
```

Open:

```text
http://localhost:3000/login
```

Use the local seeded account:

```text
Email: operator@databoom.local
Password: databoom-local
```

You can also create a new account from `/register` while
`DATABOOM_ALLOW_REGISTRATION=true`.

If the Dockerized API is running on port `8001`, start the frontend with:

```bash
cd frontend
NEXT_PUBLIC_DATABOOM_API_URL=http://localhost:8001 npm run dev -- --hostname 0.0.0.0 --port 3000
```

## Phase 2 Reviewer Smoke Test

1. Open `/login`.
2. Sign in with `operator@databoom.local` / `databoom-local`, or register a fresh account.
3. Open `/settings/subscriptions`.
4. Subscribe to Table-Boom.
5. Open `/dashboard`.
6. Select a Table-Boom source and table.
7. Generate a small run.
8. Confirm progress reaches `100%`.
9. Confirm top rows render in the table preview.
10. Download at least one CSV or SQL artifact.
11. Subscribe to Docu-Boom.
12. Generate a small document run.
13. Confirm JSON-style previews render.
14. Open `/runs` and verify both runs are listed.

## Deployment Smoke Test

Use this once Render, Supabase, and Vercel are configured.

1. Confirm Render `/ready` returns success.
2. Confirm Vercel points `NEXT_PUBLIC_DATABOOM_API_URL` to the Render API.
3. Register a reviewer account, or configure these Render variables:

```text
DATABOOM_SEED_EMAIL=<reviewer-email>
DATABOOM_SEED_NAME=<reviewer-name>
DATABOOM_SEED_PASSWORD=<reviewer-password>
```

4. Login through the Vercel URL.
5. Run the same Phase 2 reviewer smoke test.

## Phase 2 Constraints We Accept

- Artifacts are still local to the API container or attached disk.
- Async orchestration is still in-process.
- Registration may remain open for review deployments.
- LLM usage is optional and never required for generation.
- User-supplied LLM keys are not stored by the MVP.
- Masking/privacy workflows are design-only until Masker-Boom.
- Graph data is planned for Phase 3.

## Architecture Rules Carried Into Phase 3

The next architecture work should keep these rules:

- Keep product surfaces separate: relational, document, graph, and masking should share contracts, not hidden assumptions.
- Make generation plans explicit and serializable before execution.
- Keep source profiling separate from generation so the engine can run with or without source statistics.
- Keep validation and quality reporting separate: validation checks correctness, quality checks similarity to a profile.
- Keep optional AI planning behind an interface with deterministic fallback.
- Keep prompts, cache keys, and planner output schemas versioned.
- Keep artifact manifests as the source of truth for previews, downloads, validation, and later retention.
- Keep large-run performance measurable through benchmarks and operation timings.

## Phase 3 Entry Plan

Phase 3 starts with backend graph foundations, then planner and UI review surfaces.
The first active scope is Graph-Boom: graph-specific model contracts, deterministic
node and edge generation, graph artifact writers, graph validation, and API
preview/download support.

Recommended first commits:

1. `docs: start phase 3 graph boom`
2. `backend: add graph data model`
3. `backend: generate graph node and edge artifacts`
4. `backend: validate graph data artifacts`
5. `api: expose graph boom product runs`
6. `frontend: add graph workspace preview`
7. `backend: add planner interface abstraction`
8. `backend: load versioned prompt packs`
9. `optimization: add prompt cache key generation`
10. `test: add golden planner cases`

## Definition Of Phase 2 Done

Phase 2 is done when:

- Backend tests pass.
- Frontend typecheck and production build pass.
- Local login works with the seeded operator account.
- Table-Boom and Docu-Boom can each run from the dashboard.
- Runs are visible in `/runs`.
- Artifacts can be downloaded.
- Deployment docs explain Render, Supabase, Vercel, and LLM fallback behavior.
