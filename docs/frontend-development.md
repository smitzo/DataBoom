# Frontend Development Plan

The frontend should evolve in phases that match backend capability. It should be an operational workbench, not a marketing landing page.

## Stack

- Next.js.
- TypeScript.
- Tailwind CSS.
- lucide-react icons.
- API integration with the FastAPI backend in later phases.

## Design Principles

- Use Tailwind utility classes, not raw handwritten CSS.
- Keep the first screen calm and focused on one primary generation path.
- Use a single-page, scrollable workbench with progressive disclosure.
- Use wide desktop space intentionally with a product-led hero and an embedded
  control-center preview.
- Make domain profiles visible and easy to understand.
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
- Show domain profiles, output formats, pipeline steps, validation summary, and demo datasets.
- Add a roadmap section where major completed functionality is moved into
  achieved steps and future phase work stays visible.
- Keep the UI ready for API wiring without requiring the API to exist yet.

## Phase F2: Local API Integration

Backend dependency: FastAPI run endpoints.

Goals:

- Submit generation requests to the backend.
- Show run status.
- Display manifest and validation report.
- Download generated artifacts.
- Surface validation failures clearly.

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
- Add privacy policy views once Phase 4 backend privacy exists.
