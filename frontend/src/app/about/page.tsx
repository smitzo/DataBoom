import {
  ArrowLeft,
  ArrowRight,
  Check,
  Database,
  FileJson,
  GitBranch,
  ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { PublicShell } from "@/components/layout";

const designPartners = [
  {
    title: "Backend and platform teams",
    location: "Local dev / CI / staging",
    detail:
      "Need repeatable datasets that load cleanly, preserve relationships, and make integration tests less brittle.",
  },
  {
    title: "Data and analytics teams",
    location: "Warehouse / notebook / demo data",
    detail:
      "Need realistic records for analysis, dashboards, and stakeholder demos without touching protected source rows.",
  },
];

const differences = [
  {
    title: "Engine first",
    detail:
      "The product is not a prompt wrapper. Generation runs through schema parsing, planning, streaming writers, validation, and artifact manifests.",
  },
  {
    title: "Surface-specific products",
    detail:
      "Relational, document, graph, and masking workflows have different rules. DataBoom gives each one a clean product boundary.",
  },
  {
    title: "Local-first artifacts",
    detail:
      "Runs write inspectable files first: CSV, JSON, SQL, NDJSON, manifests, and reports that teams can load, diff, and archive.",
  },
  {
    title: "Sensitive-domain ready",
    detail:
      "The roadmap is shaped around fintech, healthcare, commerce, and customer data use cases where realism and control both matter.",
  },
];

const companyFacts = [
  ["Active products", "Table-Boom and Docu-Boom"],
  ["Roadmap products", "Graph-Boom and Masker-Boom"],
  ["Core stack", "Python, FastAPI, PostgreSQL, Next.js, Docker"],
  ["Product focus", "Synthetic generation, validation, export, and future masking"],
];

export default function AboutPage() {
  return (
    <PublicShell>
      <section className="border-b border-[color:var(--border)] bg-[#030405]">
        <div className="mx-auto max-w-[1120px] px-5 py-20 sm:px-8">
          <a
            href="/"
            className="inline-flex items-center gap-2 text-sm font-semibold text-[color:var(--text-muted)] transition hover:text-[color:var(--text-primary)]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </a>

          <div className="mt-16 max-w-4xl">
            <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">
              About DataBoom
            </p>
            <h1 className="mt-6 text-5xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-7xl">
              Built for teams that need useful data,{" "}
              <span className="font-serif italic text-[color:var(--text-secondary)]">
                not copies of production.
              </span>
            </h1>
            <p className="mt-8 max-w-3xl text-lg leading-8 text-[color:var(--text-muted)]">
              DataBoom is a synthetic data platform for engineering teams that need
              production-shaped datasets for development, demos, testing, and analytics
              workflows. The product is organized around data surfaces instead of demo
              domains, so use cases can grow without turning into one-off scripts.
            </p>
          </div>

          <section className="mt-20">
            <h2 className="text-3xl font-medium text-[color:var(--text-primary)]">
              Product thesis
            </h2>
            <article className="mt-6 rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-8">
              <div className="flex flex-col gap-6 md:flex-row md:items-start">
                <span className="grid h-16 w-16 shrink-0 place-items-center rounded-full border border-emerald-300/25 bg-emerald-300/10 text-emerald-300">
                  <Database className="h-7 w-7" />
                </span>
                <div>
                  <h3 className="text-2xl font-semibold text-[color:var(--text-primary)]">
                    Synthetic data should behave like infrastructure.
                  </h3>
                  <p className="mt-4 text-base leading-8 text-[color:var(--text-muted)]">
                    A good run is planned, reproducible, observable, and validated. That
                    is why DataBoom keeps the backend engine separate from product
                    surfaces like Table-Boom, Docu-Boom, Graph-Boom, and Masker-Boom.
                  </p>
                  <a
                    href="/roadmap"
                    className="mt-6 inline-flex h-11 items-center gap-2 rounded-full bg-emerald-300 px-5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
                  >
                    Read roadmap
                    <ArrowRight className="h-4 w-4" />
                  </a>
                </div>
              </div>
            </article>
          </section>

          <section className="mt-20">
            <h2 className="text-3xl font-medium text-[color:var(--text-primary)]">
              Design partners
            </h2>
            <p className="mt-4 max-w-3xl text-base leading-7 text-[color:var(--text-muted)]">
              DataBoom is shaped around teams that feel the pain of brittle fixtures,
              risky production copies, and data workflows that cannot be trusted in
              demos or CI.
            </p>
            <div className="mt-8 grid gap-5 md:grid-cols-2">
              {designPartners.map((partner) => (
                <article
                  key={partner.title}
                  className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-6"
                >
                  <h3 className="text-xl font-semibold text-[color:var(--text-primary)]">
                    {partner.title}
                  </h3>
                  <p className="mt-2 text-sm font-semibold text-[color:var(--text-faint)]">
                    {partner.location}
                  </p>
                  <p className="mt-5 text-sm leading-7 text-[color:var(--text-muted)]">
                    {partner.detail}
                  </p>
                </article>
              ))}
            </div>
            <p className="mt-6 text-sm text-[color:var(--text-muted)]">
              Building synthetic data workflows for sensitive teams?{" "}
              <a
                href="/contact"
                className="font-semibold text-[color:var(--text-primary)] underline underline-offset-4"
              >
                Get in touch
              </a>
            </p>
          </section>
        </div>
      </section>

      <section className="border-b border-[color:var(--border)] bg-[var(--section-bg)]">
        <div className="mx-auto max-w-[1120px] px-5 py-20 sm:px-8">
          <h2 className="text-4xl font-medium text-[color:var(--text-primary)]">
            What makes DataBoom{" "}
            <span className="font-serif italic text-[color:var(--text-secondary)]">
              different
            </span>
          </h2>
          <div className="mt-10 space-y-5">
            {differences.map((item) => (
              <article
                key={item.title}
                className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-6"
              >
                <h3 className="text-xl font-semibold text-[color:var(--text-primary)]">
                  {item.title}
                </h3>
                <p className="mt-3 text-base leading-7 text-[color:var(--text-muted)]">
                  {item.detail}
                </p>
              </article>
            ))}
          </div>

          <div className="mt-20 grid gap-6 lg:grid-cols-[0.45fr_1fr]">
            <div>
              <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">
                Company
              </p>
              <h2 className="mt-4 text-3xl font-medium text-[color:var(--text-primary)]">
                Product facts
              </h2>
            </div>
            <div className="space-y-3">
              {companyFacts.map(([label, value]) => (
                <div
                  key={label}
                  className="grid gap-3 rounded-lg border border-[color:var(--border)] bg-[var(--surface)] px-5 py-4 sm:grid-cols-[0.28fr_1fr]"
                >
                  <p className="text-sm font-semibold text-[color:var(--text-primary)]">
                    {label}
                  </p>
                  <p className="text-sm leading-6 text-[color:var(--text-muted)]">{value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-20 grid gap-5 md:grid-cols-3">
            <MiniCard icon={Database} label="Tables" />
            <MiniCard icon={FileJson} label="Documents" />
            <MiniCard icon={GitBranch} label="Graphs" />
            <MiniCard icon={ShieldCheck} label="Masking" />
            <MiniCard icon={Check} label="Validation" />
            <MiniCard icon={ArrowRight} label="Exports" />
          </div>
        </div>
      </section>
    </PublicShell>
  );
}

function MiniCard({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <article className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-5">
      <Icon className="h-5 w-5 text-cyan-300" />
      <p className="mt-5 text-base font-semibold text-[color:var(--text-primary)]">{label}</p>
    </article>
  );
}
