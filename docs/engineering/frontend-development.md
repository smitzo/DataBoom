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
- Keep `/` as the public landing page, then route authenticated generation work to `/dashboard`.
- Use dedicated public pages for `/products`, `/demos`, `/roadmap`, and `/contact` instead of keeping all marketing content in one long SPA.
- Use dedicated authenticated pages for login, dashboard, runs, product execution, and subscription settings.
- Use wide desktop space intentionally with operational panels, tables, and artifact actions.
- Make domain profiles visible and easy to understand.
- Make DataBoom's product family visible: Table-Boom, Docu-Boom, and Graph-Boom are active, while Masker-Boom is planned.
- Treat validation and artifacts as first-class outcomes.
- Keep components small and reusable.
- Keep public shell components reusable: launch bar, header, theme toggle, sections, and footer sitemap.
- Support public light and dark themes through shared theme tokens instead of duplicating pages.
- Render operational views from product `kind` and resource shape instead of duplicating one dashboard per product.
- Keep shared display data in one data module so roadmap steps, metrics, and
  profile cards can be updated without digging through page markup.
- Prefer scannable operational UI over decorative hero content.

## Phase F1: Static Workbench Foundation

Status: complete for the route-based public shell.

Goals:

- Create a Next.js app under `frontend/`.
- Add Tailwind.
- Build a polished public site shell.
- Split the page into reusable components under `frontend/src/components`.
- Keep product UI data under `frontend/src/data/workbench.ts`.
- Keep the first viewport uncluttered, but use the full desktop width with a
  left product story and right generation-control preview.
- Show product modules, output formats, pipeline steps, validation summary, and demo datasets on dedicated public pages.
- Add a roadmap page where major completed functionality is moved into achieved steps and future phase work stays visible.
- Add a footer sitemap so the public site behaves like a standard website.
- Keep the UI ready for API wiring without requiring the API to exist yet.

## Phase F2: Local API Integration

Backend dependency: FastAPI run endpoints.

Status: complete for the local full-stack dashboard path.

Goals:

- Register or sign in with an email/password session. `complete with backend auth and local seeded account support`
- Subscribe to product modules. `complete with API-backed subscriptions; Dockerized runs persist them in PostgreSQL`
- Submit generation requests to the backend. `complete for subscribed products`
- Show run status. `complete for synchronous local runs and run history`
- Display generated table output. `complete for synchronous local runs`
- Download generated artifacts. `complete for CSV/JSON/manifest/validation artifacts`
- Present `/dashboard` as the generic DataBoom workspace with product navigation, relational table previews, NoSQL document previews, an agent run panel, and export links. `complete`
- Render Table-Boom as a spreadsheet-style relational surface and Docu-Boom as a MongoDB-style JSON document surface from the same workspace shell. `complete`
- Test, save, refresh, and profile PostgreSQL workspace sources from the dashboard. `complete for Table-Boom sources`
- Show selected source context, schema freshness, profile state, run progress, validation state, and operation timing stages in the run builder. `complete`
- Display manifest and validation report. `partial: validation pass/fail and downloads are visible; detailed report UI is still planned`
- Surface validation failures clearly.
- Keep Masker-Boom visible as planned work; Graph-Boom now has its Phase 3 runtime preview.

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

Status: complete for proposal, review, rejection, approval, execution, and compact planner telemetry.

Goals:

- Add natural-language prompt input. `complete`
- Show prompt-to-plan output. `complete`
- Allow plan review before generation. `complete`
- Show prompt cache metrics and planner mode where useful. `complete`

## Phase F5: Production Console

Backend dependency: auth, persistence, observability, retention, and deployment hardening.

Goals:

- Add authenticated access.
- Show run history.
- Add artifact retention controls.
- Add benchmark and performance dashboards.
- Add Masker-Boom policy, redaction, tokenization, and audit views once Phase 4 backend privacy exists.
