import { ArrowRight, CheckCircle2, Clock3 } from "lucide-react";

import { ProfileCard } from "@/components/cards";
import { PublicShell, Section } from "@/components/layout";
import { profiles } from "@/data/workbench";

const productDetails = [
  {
    name: "Table-Boom",
    status: "Active",
    bestFor: "Relational schemas, QA datasets, seed data, analytics demos.",
    output: "CSV, JSON, SQL, manifest, validation report.",
    engine: "DDL ingestion, relationship graph, deterministic row generation.",
  },
  {
    name: "Docu-Boom",
    status: "Active",
    bestFor: "MongoDB-style customer profiles, orders, events, and catalog documents.",
    output: "JSON, NDJSON, manifest, validation report.",
    engine: "Collection specs, nested fields, object IDs, arrays, and references.",
  },
  {
    name: "Graph-Boom",
    status: "Planned",
    bestFor: "Fraud networks, recommendations, knowledge graphs, relationship-heavy demos.",
    output: "Planned node, edge, JSON, and CSV exports.",
    engine: "Planned node labels, edge types, cardinality, and graph validation.",
  },
  {
    name: "Masker-Boom",
    status: "Planned",
    bestFor: "Sensitive customer, fintech, medical, and operational datasets.",
    output: "Planned masked datasets, policy reports, and audit logs.",
    engine: "Planned classification, redaction, tokenization, hashing, and synthetic replacement.",
  },
];

export default function ProductsPage() {
  return (
    <PublicShell>
      <Section
        id="products"
        eyebrow="Products"
        title="Choose by data surface, not by demo domain."
        subtitle="Financial and healthcare are use cases. Products are the engines that understand table, document, graph, or masking workflows."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {profiles.map((profile) => (
            <ProfileCard key={profile.name} profile={profile} />
          ))}
        </div>
      </Section>

      <Section
        id="product-details"
        eyebrow="Catalog"
        title="What each product does."
        subtitle="This catalog keeps the runtime contract clear: each product owns a data shape, export shape, validation path, and preview surface."
      >
        <div className="space-y-4">
          {productDetails.map((product) => (
            <ProductDetail key={product.name} product={product} />
          ))}
        </div>
      </Section>

      <Section
        id="start"
        eyebrow="Run it"
        title="Use the active products from the dashboard."
        subtitle="Log in with demo credentials, subscribe to Table-Boom or Docu-Boom, generate a small run, inspect previews, and download artifacts."
      >
        <div className="rounded-lg border border-emerald-300/30 bg-emerald-300/10 p-6">
          <p className="text-lg font-semibold text-[color:var(--text-primary)]">Demo credentials</p>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
            Email: <span className="font-semibold text-emerald-300">demo</span>. Password:{" "}
            <span className="font-semibold text-emerald-300">demo</span>.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <a
              href="/login"
              className="inline-flex h-11 items-center gap-2 rounded-md bg-emerald-300 px-5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
            >
              Login
              <ArrowRight className="h-4 w-4" />
            </a>
            <a
              href="/dashboard"
              className="inline-flex h-11 items-center gap-2 rounded-md border border-[color:var(--border)] px-5 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[var(--surface)]"
            >
              Open dashboard
            </a>
          </div>
        </div>
      </Section>
    </PublicShell>
  );
}

function ProductDetail({
  product,
}: {
  product: {
    name: string;
    status: string;
    bestFor: string;
    output: string;
    engine: string;
  };
}) {
  const active = product.status === "Active";
  const Icon = active ? CheckCircle2 : Clock3;

  return (
    <article className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xl font-semibold text-[color:var(--text-primary)]">{product.name}</p>
          <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">{product.bestFor}</p>
        </div>
        <span
          className={`inline-flex w-fit items-center gap-2 rounded-md border px-3 py-2 text-xs font-semibold uppercase ${
            active
              ? "border-emerald-300/35 bg-emerald-300/10 text-emerald-300"
              : "border-sky-300/35 bg-sky-300/10 text-sky-300"
          }`}
        >
          <Icon className="h-4 w-4" />
          {product.status}
        </span>
      </div>
      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        <DetailBlock label="Output" value={product.output} />
        <DetailBlock label="Engine path" value={product.engine} />
      </div>
    </article>
  );
}

function DetailBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[color:var(--border)] bg-[var(--surface-muted)] p-4">
      <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">{label}</p>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-secondary)]">{value}</p>
    </div>
  );
}
