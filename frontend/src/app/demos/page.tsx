import { ArtifactPanel, DemoDataset, ValidationMetric } from "@/components/cards";
import { PublicShell, Section } from "@/components/layout";
import { demos, validationMetrics } from "@/data/workbench";

const useCases = [
  {
    title: "Financial records",
    detail: "Customers, accounts, transactions, payment states, and audit-friendly relational exports.",
  },
  {
    title: "Healthcare records",
    detail: "Patients, encounters, vitals, document-style profiles, and validation-friendly demo data.",
  },
  {
    title: "Commerce workflows",
    detail: "Customers, products, orders, order items, payments, events, and catalog documents.",
  },
];

export default function DemosPage() {
  return (
    <PublicShell>
      <Section
        id="demo-data"
        eyebrow="Demos"
        title="Use cases are profiles, not separate products."
        subtitle="The checked-in samples show how sensitive-domain style records can be represented without turning banking, healthcare, or commerce into separate products."
      >
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr_0.9fr]">
          {demos.map((demo) => (
            <DemoDataset key={demo.name} demo={demo} />
          ))}
          <ArtifactPanel />
        </div>
      </Section>

      <Section
        id="use-cases"
        eyebrow="Use cases"
        title="Domains change the schema and value profiles."
        subtitle="The reusable engine stays the same. A use case should provide schema, profile hints, row counts, and validation expectations."
      >
        <div className="grid gap-4 lg:grid-cols-3">
          {useCases.map((item) => (
            <article
              key={item.title}
              className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-5"
            >
              <h2 className="text-lg font-semibold text-[color:var(--text-primary)]">
                {item.title}
              </h2>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
                {item.detail}
              </p>
            </article>
          ))}
        </div>
      </Section>

      <Section
        id="validation"
        eyebrow="Validation"
        title="Demo output should always be measurable."
        subtitle="The current baseline tracks record count, runtime, memory, and validation status so performance work is grounded in evidence."
      >
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {validationMetrics.map((metric) => (
            <ValidationMetric key={metric.label} metric={metric} />
          ))}
        </div>
      </Section>
    </PublicShell>
  );
}
