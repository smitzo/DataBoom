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
- Statistical and ML model strategy:
  [Statistical and ML Synthesis Architecture](engineering/statistical-synthesis-architecture.md).
- Quality metrics, datasets, and release gates:
  [Quality Evaluation and Benchmarks](engineering/quality-evaluation-and-benchmarks.md).
- Profile v2 quality intent, bounded sampling, dependency summaries, and
  experiment lineage are owned jointly by those two engineering documents.
- GAN research, the current scikit-learn, TensorFlow, and CTGAN provider
  boundaries, dependency licensing, and experimental readiness:
  [Neural Synthesis Research](engineering/neural-synthesis-research.md).
- Local commands: [Local Development](operations/local-development.md).
- Hosted environment configuration: [Deployment Guide](operations/deployment.md).

`AGENTS.md` is the repository-level operating guide. OpenSpec owns task proposals,
requirements, designs, implementation checklists, and archived completed changes.
`understanding.md` is the backend and systems learning log; it records significant
design reasoning rather than routine change history.
