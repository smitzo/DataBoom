# Boom Data Understanding Log

This file explains what changed, why it changed, and how each change improves the project. Keep it beginner-friendly, but detailed enough that a new engineer can understand the professional reasoning behind every commit.

Every future commit must update this file.

## How To Update This File

For every commit, add a new entry using this format:

```md
## Commit: label: short summary

### What Changed

- Explain the files, modules, or behavior that changed.

### Why It Changed

- Explain the product or engineering reason.

### Why This Approach

- Explain why this design was chosen over simpler or alternative approaches.

### Performance, Reliability, or Maintainability Impact

- Explain how this affects speed, memory, correctness, scale, readability, deployment, or future work.

### Beginner Explanation

- Explain the concept in simple language for someone new to backend systems.

### Follow-Up Notes

- Mention anything intentionally deferred.
```

## Commit: docs: split product scope documents

### What Changed

- Replaced the original one-paragraph `instructions.md` with a project entry point.
- Added `docs/functional-specification.md` for product behavior and workflows.
- Added `docs/technical-design-and-roadmap.md` for architecture, stack, diagrams, phases, and commit sequencing.
- Added `docs/prompt-caching-and-instructions.md` for OpenAI prompt caching and Codex instruction hygiene.
- Added `AGENTS.md` so Codex has persistent repository guidance.

### Why It Changed

The project was too important to leave as a single rough paragraph. Boom Data needs to become a production-grade synthetic data engine, so the planning documents need separation of concerns. Product behavior, technical design, prompt strategy, and agent rules all change at different speeds and are read by different audiences.

### Why This Approach

Separating the documents prevents one giant file from becoming confusing. A product reviewer can read the functional spec. An engineer can read the technical roadmap. An agent can read `AGENTS.md`. Prompt-related decisions can live in their own file so LLM behavior is not mixed into backend implementation details.

This is better than one long instruction file because it reduces accidental edits, makes reviews easier, and lets each file stay focused.

### Performance, Reliability, or Maintainability Impact

This change does not improve runtime performance because no application code exists yet. It improves maintainability by giving future commits a clear contract. It improves reliability indirectly because future implementation work must follow documented objectives instead of improvising.

### Beginner Explanation

Think of the project like a building. Before writing code, we created separate blueprints: what the building is for, how it should be constructed, how workers should coordinate, and what rules they must follow. This makes later construction faster and less chaotic.

### Follow-Up Notes

- Implementation has not started yet.
- Phase 1 should begin with the backend engine.
- Future commits must update this file.

## Commit: docs: add product reasoning and backend implementation discipline

### What Changed

- Added `docs/product-reasoning-faq.md` to answer strategic questions using 4W1H reasoning.
- Added reasoning for why Boom Data is more than Faker.
- Added reasoning for why ChatGPT should not directly generate one million records.
- Added reasoning for how a streaming engine can eventually handle one million records.
- Added a careful comparison against Tonic.ai without claiming false universal superiority.
- Added sensitive-domain positioning for fintech, medical, insurance, and customer-sensitive workflows.
- Added this `understanding.md` file as a permanent explanation log.
- Updated `AGENTS.md` so every future commit must update this file.

### Why It Changed

The project needs clear answers to hard questions before implementation begins. People will naturally ask why this engine should exist, why an LLM alone is not enough, why we cannot just use Faker, and why we would build an internal system when commercial tools exist. Capturing those answers early keeps the team aligned.

The project also needs a durable explanation trail. Code tells us what changed, but not always why. `understanding.md` preserves the reasoning behind each decision so future contributors can learn quickly.

### Why This Approach

The FAQ is in `docs/` because it is product and architecture reasoning, not agent instruction. `understanding.md` is at the repository root because it should be visible and updated constantly.

The comparison with Faker is framed carefully: Faker is useful, but incomplete. Boom Data should use Faker for fake values while adding schema parsing, relationship solving, streaming, validation, and run management around it.

The comparison with Tonic.ai is also framed carefully. Tonic.ai is a mature commercial platform. Boom Data's argument is not "Tonic is bad"; it is "we need an owned, inspectable, local-first, PostgreSQL-focused engine that we can evolve commit by commit."

The ChatGPT reasoning separates planning from execution. LLMs are strong at interpreting intent and producing plans. They are not the right execution layer for directly emitting huge relational datasets with guaranteed constraints.

### Performance, Reliability, or Maintainability Impact

The reasoning pushes the implementation toward a streaming pipeline. That matters for performance because 100k, 500k, and eventually 1M records cannot be treated as one giant in-memory object.

The documentation also improves reliability. It says schema safety wins over prompt requests, validation is required, and privacy claims should not be made before privacy features exist.

Maintainability improves because every commit must now explain itself. A beginner can read this file and understand why decisions were made instead of reverse-engineering intent from code.

### Beginner Explanation

Faker is like a box of fake names and addresses. ChatGPT is like a smart planner that can describe what data should look like. Boom Data needs to be the factory: it reads the database blueprint, decides which tables come first, creates rows in the right order, writes files without running out of memory, and checks that everything fits.

For one million records, the factory cannot keep every item in one huge pile. It needs a conveyor belt. That is why the roadmap emphasizes chunking, streaming, manifests, and validation.

### Follow-Up Notes

- Phase 1 still starts with backend engine foundations.
- Privacy is still deferred until Phase 4, but sensitive use cases remain part of the long-term product strategy.
- A formal 1M-record benchmark should come after the 100k and 500k milestones are stable.
