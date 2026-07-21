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
- Keep the first screen focused on actual generation work.
- Make domain profiles visible and easy to understand.
- Treat validation and artifacts as first-class outcomes.
- Keep components small and reusable.
- Prefer dense, scannable operational UI over decorative hero content.

## Phase F1: Static Workbench Foundation

Status: started.

Goals:

- Create a Next.js app under `frontend/`.
- Add Tailwind.
- Build a polished static workbench shell.
- Show domain profiles, output formats, pipeline steps, validation summary, and demo datasets.
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
