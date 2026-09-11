import { PublicShell, Section } from "@/components/layout";
import { demoWorkspaces } from "@/data/demo-workspaces";

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
      <section className="border-b border-[color:var(--border)] bg-[var(--section-bg)]">
        <div className="mx-auto max-w-[1760px] px-5 py-16 sm:px-8 lg:px-12 xl:px-16">
          <div className="grid gap-8 xl:grid-cols-[0.72fr_1fr] xl:items-end">
            <div>
              <p className="text-sm font-semibold uppercase text-[color:var(--accent-emerald)]">Demo workspaces</p>
              <h1 className="mt-5 max-w-4xl text-4xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-6xl">
                Open a product dashboard without connecting a real database.
              </h1>
            </div>
            <p className="max-w-3xl text-base leading-7 text-[color:var(--text-muted)]">
              Each demo shows the same workspace shape as the app: source explorer, data preview,
              run builder, validation summary, and export controls. Choose the data surface first,
              then inspect the generated sample.
            </p>
          </div>
        </div>
      </section>

      <Section
        id="demo-workspaces"
        eyebrow="Choose"
        title="Pick the product workspace you want to inspect."
        subtitle="Table-Boom and Docu-Boom show active full-stack flows. Graph-Boom and Masker-Boom stay visible as roadmap surfaces."
      >
        <div className="grid gap-4 lg:grid-cols-2">
          {demoWorkspaces.map((workspace) => (
            <a
              key={workspace.id}
              className="group rounded-xl border border-[color:var(--border)] bg-[var(--surface)] p-5 transition duration-300 hover:-translate-y-1 hover:bg-[var(--surface-strong)]"
              href={`/demos/${workspace.id}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold uppercase text-[color:var(--accent-emerald)]">
                    {workspace.module}
                  </p>
                  <h2 className="mt-3 text-2xl font-semibold text-[color:var(--text-primary)]">
                    {workspace.name}
                  </h2>
                </div>
                <span className="rounded-md border border-cyan-300/25 bg-cyan-300/10 px-3 py-1 text-xs font-semibold uppercase text-[color:var(--accent-cyan)]">
                  {workspace.kind === "planned" ? "Roadmap" : "Open demo"}
                </span>
              </div>
              <p className="mt-4 text-sm leading-6 text-[color:var(--text-muted)]">
                {workspace.description}
              </p>
              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                <DemoStat label="Rows" value={String(workspace.rows)} />
                <DemoStat
                  label={workspace.kind === "document" ? "Collections" : "Tables"}
                  value={String(workspace.resources.length)}
                />
                <DemoStat label="Artifacts" value={String(workspace.artifacts)} />
              </div>
            </a>
          ))}
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
              className="rounded-xl border border-[color:var(--border)] bg-[var(--surface)] p-5"
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

    </PublicShell>
  );
}

function DemoStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[color:var(--border)] bg-[var(--surface-muted)] p-3">
      <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[color:var(--text-primary)]">{value}</p>
    </div>
  );
}
