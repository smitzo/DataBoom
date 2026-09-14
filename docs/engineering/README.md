# Engineering Documentation

This folder explains how DataBoom is designed and how it evolves. Read documents
from broad system boundaries toward implementation detail.

## Design

- [High-Level Design](high-level-design.md): system context, component boundaries,
  data flows, planner review, deployment topology, and extensibility.
- [Low-Level Design](low-level-design.md): Python module ownership, contracts,
  execution sequences, persistence, artifacts, and failure boundaries.
- [Engineering Standards](engineering-standards.md): reusable-code, product-kind,
  route, component, and test rules.

## Delivery

- [Roadmap](roadmap.md): five phases, current status, objectives, and commit order.
- [Optimization Plan](optimization-plan.md): measured performance and quality work.
- [Frontend Development](frontend-development.md): UI phases aligned with backend
  capability.
- [LLM Planning and Prompt Caching](prompt-caching-and-instructions.md): versioned
  prompt packs, strict output contracts, cache keys, metrics, and agent guidance.

## Ownership Rule

HLD owns system boundaries. LLD owns class/module behavior. The roadmap owns
status. Do not copy complete diagrams or phase checklists between these files;
link to the canonical document instead.
