# Product Documentation

Use this folder for what DataBoom is, who it serves, and what each product must
do. Implementation details belong in `docs/engineering`; setup commands belong
in `docs/operations`.

## Documents

- [Functional Specification](functional-specification.md): canonical behavior,
  workflows, requirements, boundaries, and acceptance criteria.
- [Product Family](product-family.md): canonical Table-Boom, Docu-Boom,
  Graph-Boom, and Masker-Boom taxonomy.
- [Product Reasoning FAQ](product-reasoning-faq.md): 4W1H reasoning, alternatives,
  scale questions, and sensitive-domain positioning.
- [Design Research](design-research.md): product and workflow lessons from
  adjacent tools; research is not an implementation contract.

## Update Rule

Change the functional specification when product behavior changes. Change the
product family only when catalog ownership or product-kind boundaries change.
Keep implementation status in the engineering roadmap instead of duplicating a
second roadmap here.
