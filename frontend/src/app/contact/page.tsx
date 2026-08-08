import {
  ArrowRight,
  Building2,
  CalendarCheck,
  Database,
  FileText,
  Mail,
  MapPinned,
  MessageSquare,
  Send,
  ShieldCheck,
  TerminalSquare,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { PublicShell, Section } from "@/components/layout";

const contactBlocks = [
  {
    icon: TerminalSquare,
    title: "Evaluate locally",
    detail: "Run the Docker API, start the Next.js frontend, and use demo/demo to test the current Table-Boom and Docu-Boom flow.",
  },
  {
    icon: MapPinned,
    title: "Choose the surface",
    detail: "Start with relational tables, document collections, graph plans, or a masking requirement so the scope stays concrete.",
  },
  {
    icon: ShieldCheck,
    title: "Define integrity",
    detail: "Bring row counts, key rules, reference rules, export formats, and validation expectations before generation starts.",
  },
];

const checklist = [
  "Data surface: Table-Boom, Docu-Boom, Graph-Boom, or Masker-Boom.",
  "Target volume: local demo, 100k, 500k, 1M, or a benchmark target.",
  "Integrity rules: primary keys, foreign keys, document references, graph edges, or masking links.",
  "Export shape: CSV, JSON, SQL, NDJSON, manifest, validation report, or future connector.",
  "Deployment path: local CLI, Docker API, dashboard workflow, CI artifact job, or hosted environment.",
  "Privacy scope: fully synthetic now, redaction and masking policy later.",
];

const formFields = [
  { label: "Name", placeholder: "Smit Joshi", type: "text" },
  { label: "Work email", placeholder: "team@databoom.dev", type: "email" },
  { label: "Company", placeholder: "Fintech, healthcare, SaaS, ecommerce...", type: "text" },
  { label: "Target volume", placeholder: "100k rows, 500k docs, 1M edges...", type: "text" },
];

export default function ContactPage() {
  return (
    <PublicShell>
      <section className="border-b border-[color:var(--border)] bg-[var(--section-bg)]">
        <div className="mx-auto grid max-w-[1680px] gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:px-12 xl:px-16">
          <div>
            <p className="text-sm font-semibold uppercase text-emerald-300">Contact</p>
            <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-tight text-[color:var(--text-primary)] lg:text-6xl">
              Bring the schema. We will shape the generation plan.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-[color:var(--text-muted)]">
              DataBoom works best when the conversation starts with a clear data surface,
              target size, integrity rules, export format, and validation requirement.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a
                href="/login"
                className="inline-flex h-12 items-center gap-2 rounded-md bg-emerald-300 px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
              >
                Open demo login
                <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="/products"
                className="inline-flex h-12 items-center gap-2 rounded-md border border-[color:var(--border)] px-6 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[var(--surface)]"
              >
                Review products
              </a>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            {contactBlocks.map((item) => {
              const Icon = item.icon;
              return (
                <article
                  key={item.title}
                  className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-5 transition duration-300 hover:-translate-y-1 hover:bg-[var(--surface-strong)]"
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
        </div>
      </section>

      <Section
        id="brief"
        eyebrow="Implementation brief"
        title="A good request contains enough structure to test the engine."
        subtitle="This scaffold keeps the future contact workflow product-focused instead of collecting vague marketing messages."
      >
        <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <form className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-md bg-emerald-300/10 text-emerald-300">
                <MessageSquare className="h-5 w-5" />
              </span>
              <div>
                <p className="font-semibold text-[color:var(--text-primary)]">Request scaffold</p>
                <p className="text-sm text-[color:var(--text-muted)]">Form wiring comes with the hosted contact backend.</p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {formFields.map((field) => (
                <label key={field.label} className="block">
                  <span className="text-sm font-semibold text-[color:var(--text-secondary)]">
                    {field.label}
                  </span>
                  <input
                    className="mt-2 h-12 w-full rounded-md border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-emerald-300/60"
                    placeholder={field.placeholder}
                    type={field.type}
                  />
                </label>
              ))}
            </div>

            <label className="mt-4 block">
              <span className="text-sm font-semibold text-[color:var(--text-secondary)]">
                What should DataBoom generate or mask?
              </span>
              <textarea
                className="mt-2 h-36 w-full resize-none rounded-md border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-emerald-300/60"
                placeholder="Example: Generate 500k ecommerce orders with customers, products, payments, refunds, and validation reports."
              />
            </label>

            <button
              className="mt-5 inline-flex h-12 items-center gap-2 rounded-md bg-emerald-300 px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
              type="button"
            >
              Save request draft
              <Send className="h-4 w-4" />
            </button>
          </form>

          <div className="grid gap-4">
            <article className="rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-5">
              <div className="flex items-center gap-3">
                <CalendarCheck className="h-5 w-5 text-cyan-200" />
                <p className="font-semibold text-[color:var(--text-primary)]">Evaluation checklist</p>
              </div>
              <div className="mt-5 space-y-3">
                {checklist.map((item) => (
                  <p key={item} className="text-sm leading-6 text-[color:var(--text-secondary)]">
                    {item}
                  </p>
                ))}
              </div>
            </article>

            <div className="grid gap-4 md:grid-cols-2">
              <ContactRoute icon={Database} title="Product fit" detail="Use `/products` to pick the data surface." />
              <ContactRoute icon={FileText} title="Demo evidence" detail="Use `/demos` to review checked-in CSV examples." />
              <ContactRoute icon={Building2} title="Roadmap" detail="Use `/roadmap` to see what is active, next, and planned." />
              <ContactRoute icon={Mail} title="Follow-up" detail="Replace this scaffold with CRM or email delivery in a later deployment phase." />
            </div>
          </div>
        </div>
      </Section>
    </PublicShell>
  );
}

function ContactRoute({
  icon: Icon,
  title,
  detail,
}: {
  icon: LucideIcon;
  title: string;
  detail: string;
}) {
  return (
    <article className="rounded-lg border border-[color:var(--border)] bg-[var(--surface-muted)] p-4">
      <Icon className="h-4 w-4 text-emerald-300" />
      <p className="mt-4 font-semibold text-[color:var(--text-primary)]">{title}</p>
      <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">{detail}</p>
    </article>
  );
}
