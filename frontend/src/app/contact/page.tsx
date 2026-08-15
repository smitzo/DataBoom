import {
  ArrowRight,
  Database,
  GitBranch,
  MessageSquare,
  Send,
  ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { PublicShell } from "@/components/layout";

const briefItems = [
  "Data shape: relational tables, document collections, graph data, or masking.",
  "Target scale: demo sample, 100k rows, 500k rows, or a larger benchmark.",
  "Integrity rules: keys, references, document IDs, graph edges, or masking links.",
  "Output contracts: CSV, JSON, SQL, NDJSON, manifest, validation report, or download flow.",
];

const formFields = [
  { label: "Name", placeholder: "Your name", type: "text" },
  { label: "Email", placeholder: "you@company.com", type: "email" },
  { label: "Company", placeholder: "Fintech, healthcare, SaaS, ecommerce...", type: "text" },
  { label: "Target volume", placeholder: "100k rows, 500k docs, 1M edges...", type: "text" },
];

export default function ContactPage() {
  return (
    <PublicShell>
      <section className="border-b border-[color:var(--border)] bg-[#030405]">
        <div className="mx-auto max-w-[1120px] px-5 py-20 sm:px-8">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">
              Contact
            </p>
            <h1 className="mt-6 text-5xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-7xl">
              Bring the schema. We will shape the generation plan.
            </h1>
            <p className="mt-8 text-lg leading-8 text-[color:var(--text-muted)]">
              Tell us what DataBoom needs to generate, mask, validate, or export. The
              clearest requests include data shape, scale, integrity rules, output
              formats, and deployment expectations.
            </p>
          </div>

          <div className="mt-16 grid gap-8 lg:grid-cols-[1fr_0.72fr]">
            <form className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-7">
              <div className="grid gap-5 md:grid-cols-2">
                {formFields.map((field) => (
                  <label key={field.label} className="block">
                    <span className="text-xs font-semibold uppercase text-[color:var(--text-muted)]">
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

              <label className="mt-5 block">
                <span className="text-xs font-semibold uppercase text-[color:var(--text-muted)]">
                  What is this about?
                </span>
                <select className="mt-2 h-12 w-full rounded-md border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-emerald-300/60">
                  <option>Generate relational data</option>
                  <option>Generate document data</option>
                  <option>Plan graph data</option>
                  <option>Mask or redact sensitive data</option>
                  <option>General inquiry</option>
                </select>
              </label>

              <label className="mt-5 block">
                <span className="text-xs font-semibold uppercase text-[color:var(--text-muted)]">
                  Message
                </span>
                <textarea
                  className="mt-2 h-40 w-full resize-none rounded-md border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-emerald-300/60"
                  placeholder="Example: Generate 500k ecommerce orders with customers, products, payments, refunds, and validation reports."
                />
              </label>

              <button
                className="mt-7 inline-flex h-12 items-center gap-2 rounded-full bg-white px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
                type="button"
              >
                Send message
                <Send className="h-4 w-4" />
              </button>

              <p className="mt-7 text-sm text-[color:var(--text-faint)]">
                This scaffold can be wired to email, CRM, or a backend route during
                deployment hardening.
              </p>
            </form>

            <aside className="space-y-5">
              <article className="rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-6">
                <MessageSquare className="h-5 w-5 text-cyan-200" />
                <h2 className="mt-5 text-xl font-semibold text-[color:var(--text-primary)]">
                  What to include
                </h2>
                <div className="mt-5 space-y-3">
                  {briefItems.map((item) => (
                    <p key={item} className="text-sm leading-7 text-[color:var(--text-secondary)]">
                      {item}
                    </p>
                  ))}
                </div>
              </article>

              <ContactRoute
                icon={Database}
                title="Use the active workspace"
                detail="Log in with demo/demo, subscribe to Table-Boom or Docu-Boom, generate a run, preview output, and download artifacts."
                href="/dashboard"
              />
              <ContactRoute
                icon={ShieldCheck}
                title="Review product boundaries"
                detail="See how Table-Boom, Docu-Boom, Graph-Boom, and Masker-Boom are separated by data shape."
                href="/products"
              />
              <ContactRoute
                icon={GitBranch}
                title="Read the roadmap"
                detail="Check what is active, what is hardening next, and what belongs to future phases."
                href="/roadmap"
              />
            </aside>
          </div>

          <div className="mt-20 border-t border-[color:var(--border)] pt-12 text-center">
            <p className="text-xl text-[color:var(--text-secondary)]">
              See what your test data workflow is{" "}
              <span className="font-serif italic text-[color:var(--text-primary)]">
                really costing you.
              </span>
            </p>
            <div className="mt-8 flex justify-center gap-3">
              <a
                href="/dashboard"
                className="inline-flex h-12 items-center rounded-full bg-white px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
              >
                Open dashboard
              </a>
              <a
                href="/products"
                className="inline-flex h-12 items-center gap-2 rounded-full border border-[color:var(--border)] px-6 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[var(--surface)]"
              >
                See products
                <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      </section>
    </PublicShell>
  );
}

function ContactRoute({
  icon: Icon,
  title,
  detail,
  href,
}: {
  icon: LucideIcon;
  title: string;
  detail: string;
  href: string;
}) {
  return (
    <a
      href={href}
      className="block rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-5 transition hover:bg-[var(--surface-strong)]"
    >
      <Icon className="h-5 w-5 text-emerald-300" />
      <h3 className="mt-5 text-lg font-semibold text-[color:var(--text-primary)]">{title}</h3>
      <p className="mt-3 text-sm leading-7 text-[color:var(--text-muted)]">{detail}</p>
    </a>
  );
}
