import { ArrowRight, Mail, MapPinned, TerminalSquare } from "lucide-react";

import { PublicShell, Section } from "@/components/layout";

const contactBlocks = [
  {
    icon: TerminalSquare,
    title: "Try the local product",
    detail: "Run the Dockerized API, start the Next.js frontend, and use demo/demo to test Table-Boom and Docu-Boom.",
  },
  {
    icon: MapPinned,
    title: "Discuss a data surface",
    detail: "Use Table-Boom for relational data, Docu-Boom for documents, Graph-Boom for graph plans, or Masker-Boom for privacy plans.",
  },
  {
    icon: Mail,
    title: "Prepare an implementation brief",
    detail: "Share target schema shape, data volume, output formats, validation needs, and whether data is generated or masked.",
  },
];

export default function ContactPage() {
  return (
    <PublicShell>
      <Section
        id="contact"
        eyebrow="Contact"
        title="Bring a schema, target volume, and output requirement."
        subtitle="DataBoom discussions should be concrete: data surface, row/document count, integrity rules, export format, and validation needs."
      >
        <div className="grid gap-4 lg:grid-cols-3">
          {contactBlocks.map((item) => {
            const Icon = item.icon;
            return (
              <article
                key={item.title}
                className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-5"
              >
                <Icon className="h-5 w-5 text-emerald-300" />
                <h2 className="mt-5 text-lg font-semibold text-[color:var(--text-primary)]">
                  {item.title}
                </h2>
                <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
                  {item.detail}
                </p>
              </article>
            );
          })}
        </div>

        <div className="mt-6 rounded-lg border border-emerald-300/30 bg-emerald-300/10 p-6">
          <p className="text-lg font-semibold text-[color:var(--text-primary)]">
            Evaluation checklist
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {[
              "Data surface: relational, document, graph, or masking.",
              "Target volume: 100k, 500k, 1M, or smaller local demos.",
              "Integrity rules: primary keys, foreign keys, references, or graph edges.",
              "Export shape: CSV, JSON, SQL, NDJSON, manifest, validation report.",
              "Deployment path: local CLI, Docker API, dashboard workflow, or CI artifact generation.",
              "Privacy scope: generated synthetic data now, masking/redaction later.",
            ].map((item) => (
              <p key={item} className="text-sm leading-6 text-[color:var(--text-secondary)]">
                {item}
              </p>
            ))}
          </div>
          <a
            href="/login"
            className="mt-6 inline-flex h-11 items-center gap-2 rounded-md bg-emerald-300 px-5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
          >
            Open demo login
            <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </Section>
    </PublicShell>
  );
}
