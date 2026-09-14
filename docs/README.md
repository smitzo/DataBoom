# DataBoom Documentation

The documentation has three ownership areas. Start with the index for the area
you are changing; each index identifies the canonical document for a topic and
prevents architecture, product scope, and run instructions from drifting into
each other.

## Documentation Map

| Area | Owns | Start here |
| --- | --- | --- |
| [Product](product/README.md) | Product family, users, workflows, scope, positioning, and research. | [Functional Specification](product/functional-specification.md) |
| [Engineering](engineering/README.md) | HLD, LLD, roadmap, standards, optimization, frontend, and LLM planning. | [High-Level Design](engineering/high-level-design.md) |
| [Operations](operations/README.md) | Local setup, deployment, smoke tests, and completed phase handoffs. | [Local Development](operations/local-development.md) |

## Canonical Sources

- Product behavior: [Functional Specification](product/functional-specification.md).
- Product names and data surfaces: [Product Family](product/product-family.md).
- System boundaries and deployment topology: [High-Level Design](engineering/high-level-design.md).
- Python modules, contracts, and runtime sequences: [Low-Level Design](engineering/low-level-design.md).
- Current phase and future objectives: [Roadmap](engineering/roadmap.md).
- Local commands: [Local Development](operations/local-development.md).
- Hosted environment configuration: [Deployment Guide](operations/deployment.md).

`instructions.md` and `AGENTS.md` are repository-level operating instructions,
not product documentation. `understanding.md` is the backend and systems learning
log; it records significant design reasoning rather than routine change history.
