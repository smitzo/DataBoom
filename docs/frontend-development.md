# Frontend Development Plan

The frontend should evolve in phases that match backend capability. It should be an operational workbench, not a marketing landing page.

## Stack

- Next.js.
- TypeScript.
- Tailwind CSS.
- lucide-react icons.
- API integration with the FastAPI backend.

## Design Principles

- Use Tailwind utility classes, not raw handwritten CSS.
- Keep the dashboard calm and focused on the primary subscription-to-generation path.
- Keep `/` as the public hero/product page, then route authenticated work to `/dashboard`.
- Use dedicated pages for login, dashboard, products, runs, and roadmap once backend capability exists.
- Use wide desktop space intentionally with operational panels, tables, and artifact actions.
- Make domain profiles visible and easy to understand.
- Make DataBoom's product family visible: Generator-Boom is active now, while Masker-Boom is the planned privacy layer.
- Treat validation and artifacts as first-class outcomes.
- Keep components small and reusable.
- Keep shared display data in one data module so roadmap steps, metrics, and
  profile cards can be updated without digging through page markup.
- Prefer scannable operational UI over decorative hero content.

## Phase F1: Static Workbench Foundation

Status: complete for the static shell.

Goals:

- Create a Next.js app under `frontend/`.
- Add Tailwind.
- Build a polished static single-page workbench shell.
- Split the page into reusable components under `frontend/src/components`.
- Keep product UI data under `frontend/src/data/workbench.ts`.
- Keep the first viewport uncluttered, but use the full desktop width with a
  left product story and right generation-control preview.
- Show product modules, output formats, pipeline steps, validation summary, and demo datasets.
- Add a roadmap section where major completed functionality is moved into
  achieved steps and future phase work stays visible.
- Keep the UI ready for API wiring without requiring the API to exist yet.

## Phase F2: Local API Integration

Backend dependency: FastAPI run endpoints.

Status: complete for the local full-stack dashboard path.

Goals:

- Login with the demo user. `complete with demo/demo credentials`
- Subscribe to product modules. `complete with API-backed subscriptions; Dockerized runs persist them in PostgreSQL`
- Submit generation requests to the backend. `complete for subscribed products`
- Show run status. `complete for synchronous local runs and run history`
- Display generated table output. `complete for synchronous local runs`
- Download generated artifacts. `complete for CSV/JSON/manifest/validation artifacts`
- Display manifest and validation report. `partial: validation pass/fail and downloads are visible; detailed report UI is still planned`
- Surface validation failures clearly.
- Keep Masker-Boom visible as planned work without building masking UI before Phase 4.

## Phase F3: Schema and Domain Builder

Backend dependency: richer planning and domain profile configuration.

Goals:

- Upload or paste PostgreSQL DDL.
- Preview parsed tables and relationships.
- Choose domain profile per table or per run.
- Configure row counts and output formats.
- Preview dry-run generation plans.

## Phase F4: LLM-Assisted Planning UX

Backend dependency: LLM planner interface and prompt packs.

Goals:

- Add natural-language prompt input.
- Show prompt-to-plan output.
- Allow plan review before generation.
- Show prompt cache metrics and planner version where useful.

## Phase F5: Production Console

Backend dependency: auth, persistence, observability, retention, and deployment hardening.

Goals:

- Add authenticated access.
- Show run history.
- Add artifact retention controls.
- Add benchmark and performance dashboards.
- Add Masker-Boom policy, redaction, tokenization, and audit views once Phase 4 backend privacy exists.
