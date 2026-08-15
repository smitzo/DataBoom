import {
  ArrowRight,
  Check,
  Database,
  Download,
  FileJson,
  GitBranch,
  KeyRound,
  Layers3,
  Plus,
  ShieldCheck,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const overviewCards = [
  {
    title: "One engine, not ten scripts",
    detail:
      "Replace one-off Faker files, hand-written SQL seeds, and spreadsheet fixtures with planned runs that produce validated artifacts.",
  },
  {
    title: "Products by data shape",
    detail:
      "Table-Boom, Docu-Boom, Graph-Boom, and Masker-Boom separate relational, document, graph, and masking workflows cleanly.",
  },
  {
    title: "Built for sensitive domains",
    detail:
      "Fintech, healthcare, commerce, and customer datasets need realism without copying records from production systems.",
  },
];

const oldWay = [
  "Fake values look fine until foreign keys, dates, balances, and nested records need to agree.",
  "Chat prompts produce samples, not a repeatable million-row data run with validation and downloads.",
  "Production copies create privacy risk, stale fixtures, and local environments nobody fully trusts.",
];

const newWay = [
  "A schema-aware planner understands tables, documents, references, and target volumes before generation starts.",
  "The engine streams deterministic records into CSV, JSON, SQL, NDJSON, manifests, and validation reports.",
  "The dashboard tracks status, previews output, exposes timings, and keeps each product surface modular.",
];

const productGroups = [
  {
    name: "Table-Boom",
    eyebrow: "Relational engine",
    status: "Live in workspace",
    statusClass: "border-emerald-300/30 bg-emerald-300/10 text-emerald-200",
    tone: "text-emerald-300 border-emerald-300/25 bg-emerald-300/10",
    border: "border-emerald-300/25",
    bar: "from-emerald-300 via-cyan-300 to-transparent",
    glow: "bg-emerald-300/10",
    icon: Database,
    description:
      "Generate relational datasets with stable keys, foreign-key-safe children, validation manifests, and CSV/JSON/SQL exports.",
    ctaLabel: "Open workspace",
    ctaHref: "/dashboard",
    items: [
      "PostgreSQL schema ingestion",
      "Primary and foreign key preservation",
      "CSV, JSON, and SQL exports",
      "Financial and healthcare profiles",
      "Validation manifests",
      "Run telemetry",
    ],
  },
  {
    name: "Docu-Boom",
    eyebrow: "Document engine",
    status: "Live in workspace",
    statusClass: "border-cyan-300/30 bg-cyan-300/10 text-cyan-200",
    tone: "text-cyan-300 border-cyan-300/25 bg-cyan-300/10",
    border: "border-cyan-300/25",
    bar: "from-cyan-300 via-sky-300 to-transparent",
    glow: "bg-cyan-300/10",
    icon: FileJson,
    description:
      "Create MongoDB-style JSON and NDJSON collections with nested fields, stable document identifiers, previews, and collection reports.",
    ctaLabel: "Open workspace",
    ctaHref: "/dashboard",
    items: [
      "Nested JSON documents",
      "NDJSON collection exports",
      "Stable document identifiers",
      "Top-document previews",
      "Collection manifests",
      "Document validation",
    ],
  },
  {
    name: "Graph-Boom",
    eyebrow: "Graph roadmap",
    status: "Roadmap",
    statusClass: "border-sky-300/30 bg-sky-300/10 text-sky-200",
    tone: "text-sky-300 border-sky-300/25 bg-sky-300/10",
    border: "border-sky-300/25",
    bar: "from-sky-300 via-indigo-300 to-transparent",
    glow: "bg-sky-300/10",
    icon: GitBranch,
    description:
      "Planned graph generation for nodes, edges, relationship density, cardinality rules, and connected-data previews.",
    ctaLabel: "View roadmap",
    ctaHref: "/roadmap",
    items: [
      "Node and edge generation",
      "Cardinality rules",
      "Relationship-heavy datasets",
      "Graph previews",
    ],
  },
  {
    name: "Masker-Boom",
    eyebrow: "Masking roadmap",
    status: "Roadmap",
    statusClass: "border-amber-300/30 bg-amber-300/10 text-amber-200",
    tone: "text-amber-300 border-amber-300/25 bg-amber-300/10",
    border: "border-amber-300/25",
    bar: "from-amber-300 via-emerald-300 to-transparent",
    glow: "bg-amber-300/10",
    icon: ShieldCheck,
    description:
      "Planned masking layer for redaction, tokenization, synthetic replacement, and privacy reports over sensitive source data.",
    ctaLabel: "View roadmap",
    ctaHref: "/roadmap",
    items: [
      "Redaction policies",
      "Stable tokenization",
      "Synthetic replacement",
      "Privacy reports",
    ],
  },
];

const controls = [
  {
    icon: KeyRound,
    title: "Deterministic runs",
    detail: "Seeds make a generated dataset reproducible, debuggable, and useful in CI.",
  },
  {
    icon: Layers3,
    title: "Integrity first",
    detail: "References, row counts, manifests, and validations are treated as part of the product contract.",
  },
  {
    icon: Download,
    title: "Portable artifacts",
    detail: "Runs write local files first so teams can inspect, version, load, and download the exact output.",
  },
  {
    icon: ShieldCheck,
    title: "Privacy boundary",
    detail: "Masker-Boom is kept separate so redaction and source-data workflows can harden behind policy controls.",
  },
];

const questions = [
  {
    question: "Why not just use Faker?",
    answer:
      "Faker generates plausible field values. DataBoom plans full datasets: tables, documents, relationships, target volumes, exports, validation, and run telemetry.",
  },
  {
    question: "Why can't ChatGPT generate one million records directly?",
    answer:
      "LLMs are useful for planning and schema interpretation, but high-volume generation needs streaming execution, deterministic seeds, memory control, validation, and artifact writing.",
  },
  {
    question: "How is this different from Tonic or Gretel?",
    answer:
      "Those are mature synthetic-data platforms. DataBoom is being built as an open, local-first engine with explicit product surfaces for relational, document, graph, and masking workflows.",
  },
  {
    question: "Can DataBoom generate fintech or healthcare-style data?",
    answer:
      "Yes. Domains are profiles on top of the engine. Finance, healthcare, commerce, and SaaS data change schemas and value distributions, not the core run lifecycle.",
  },
  {
    question: "Do I need to upload production data?",
    answer:
      "No for the current synthetic generation flow. Phase 1 and Phase 2 focus on schema and profile-driven generation. Source-data masking arrives later through Masker-Boom.",
  },
  {
    question: "What is active today?",
    answer:
      "Table-Boom and Docu-Boom are active in the full-stack workspace. Graph-Boom and Masker-Boom are visible in the roadmap so their boundaries stay clear.",
  },
];

export function MarketingStory() {
  return (
    <>
      <WhatIsDataBoom />
      <ProblemFix />
      <ProductSystem />
      <TrustAndFaq />
    </>
  );
}

function WhatIsDataBoom() {
  return (
    <section id="what-is-databoom" className="border-b border-[color:var(--border)] bg-[#030405]">
      <div className="mx-auto max-w-[1180px] px-5 py-24 sm:px-8">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">
            What is DataBoom?
          </p>
          <h2 className="mt-6 text-4xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-6xl">
            A synthetic data engine for teams that cannot use production as a shortcut.
          </h2>
          <p className="mt-6 text-lg leading-8 text-[color:var(--text-muted)]">
            DataBoom turns schemas and product requirements into repeatable runs. Instead
            of stitching together scripts, seed dumps, and chat-generated samples, your
            team generates data, validates it, previews it, and exports artifacts from one
            workspace.
          </p>
        </div>

        <div className="mt-14 grid gap-5 lg:grid-cols-3">
          {overviewCards.map((card) => (
            <TextCard key={card.title} title={card.title} detail={card.detail} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ProblemFix() {
  return (
    <section className="border-b border-[color:var(--border)] bg-[var(--section-bg)]">
      <div className="mx-auto max-w-[1180px] px-5 py-24 sm:px-8">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase text-red-300">The problem</p>
          <h2 className="mt-5 text-4xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-6xl">
            Test data should not break the moment it starts looking real.
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-[color:var(--text-muted)]">
            The hard part is not a name, email, or date. It is the structure around those
            values: relationships, constraints, distribution, volume, and proof.
          </p>
        </div>

        <div className="mt-14 grid gap-5 lg:grid-cols-3">
          {oldWay.map((item) => (
            <SignalCard key={item} tone="danger" icon={X} detail={item} />
          ))}
        </div>

        <div className="mt-24 text-center">
          <p className="text-xs font-semibold uppercase text-emerald-300">The fix</p>
          <h2 className="mt-5 text-4xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-6xl">
            DataBoom makes generation a controlled run.
          </h2>
        </div>

        <div className="mt-14 grid gap-5 lg:grid-cols-3">
          {newWay.map((item) => (
            <SignalCard key={item} tone="success" icon={Check} detail={item} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ProductSystem() {
  return (
    <section id="product-system" className="border-b border-[color:var(--border)] bg-[#030405]">
      <div className="mx-auto max-w-[1240px] px-5 py-24 sm:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">
            Product surfaces
          </p>
          <h2 className="mt-5 text-4xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-6xl">
            Four product surfaces, clearly separated.
          </h2>
          <p className="mt-6 text-lg leading-8 text-[color:var(--text-muted)]">
            Data shape drives the workflow. Use cases like banking, healthcare, commerce,
            and customer support become profiles inside the right product engine.
          </p>
        </div>

        <div className="mt-16 grid gap-6 lg:grid-cols-2">
          {productGroups.map((group) => (
            <ProductModuleCard key={group.name} group={group} />
          ))}
        </div>

        <div className="mt-16 text-center">
          <a
            href="/products"
            className="inline-flex h-12 items-center gap-2 rounded-full border border-[color:var(--border)] px-6 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[var(--surface)]"
          >
            See product catalog
            <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </div>
    </section>
  );
}

function TrustAndFaq() {
  return (
    <section className="border-b border-[color:var(--border)] bg-[var(--section-bg)]">
      <div className="mx-auto max-w-[1180px] px-5 py-24 sm:px-8">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">
            Trust model
          </p>
          <h2 className="mt-6 text-4xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-6xl">
            Sensitive workflows deserve data you can audit.
          </h2>
          <p className="mt-6 text-lg leading-8 text-[color:var(--text-muted)]">
            DataBoom keeps the engine explicit: planned inputs, deterministic execution,
            local artifacts, validation reports, and a clear boundary for future masking.
          </p>
        </div>

        <div className="mt-14 grid gap-5 md:grid-cols-2">
          {controls.map((control) => (
            <IconCard key={control.title} item={control} />
          ))}
        </div>

        <div className="mx-auto mt-24 max-w-3xl">
          <h2 className="text-center text-4xl font-medium text-[color:var(--text-primary)]">
            Common questions
          </h2>
          <div className="mt-12">
            {questions.map((item) => (
              <details
                key={item.question}
                className="group border-b border-[color:var(--border)] py-5"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-base font-semibold text-[color:var(--text-primary)]">
                  {item.question}
                  <Plus className="h-5 w-5 shrink-0 text-[color:var(--text-faint)] transition group-open:rotate-45" />
                </summary>
                <p className="mt-4 text-sm leading-7 text-[color:var(--text-muted)]">
                  {item.answer}
                </p>
              </details>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function TextCard({ title, detail }: { title: string; detail: string }) {
  return (
    <article className="min-h-52 rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-6">
      <h3 className="text-xl font-semibold text-[color:var(--text-primary)]">{title}</h3>
      <p className="mt-4 text-sm leading-7 text-[color:var(--text-muted)]">{detail}</p>
    </article>
  );
}

function SignalCard({
  tone,
  icon: Icon,
  detail,
}: {
  tone: "danger" | "success";
  icon: LucideIcon;
  detail: string;
}) {
  const toneClass =
    tone === "danger"
      ? "border-red-400/20 bg-red-400/5 text-red-300"
      : "border-emerald-300/20 bg-emerald-300/5 text-emerald-300";

  return (
    <article className={`rounded-lg border p-6 ${toneClass}`}>
      <Icon className="h-5 w-5" />
      <p className="mt-5 text-base font-medium leading-7 text-[color:var(--text-secondary)]">
        {detail}
      </p>
    </article>
  );
}

function ProductModuleCard({
  group,
}: {
  group: {
    name: string;
    eyebrow: string;
    status: string;
    statusClass: string;
    tone: string;
    border: string;
    bar: string;
    glow: string;
    icon: LucideIcon;
    description: string;
    ctaLabel: string;
    ctaHref: string;
    items: string[];
  };
}) {
  const Icon = group.icon;

  return (
    <article
      className={`relative overflow-hidden rounded-2xl border bg-[var(--surface)] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.18)] ${group.border}`}
    >
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${group.bar}`} />
      <div
        className={`pointer-events-none absolute -right-20 -top-24 h-56 w-56 rounded-full blur-3xl ${group.glow}`}
        aria-hidden="true"
      />

      <div className="relative">
        <div className="flex items-start justify-between gap-5">
          <div className="flex items-center gap-4">
            <span className={`grid h-14 w-14 place-items-center rounded-2xl border ${group.tone}`}>
              <Icon className="h-6 w-6" />
            </span>
            <div>
              <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">
                {group.eyebrow}
              </p>
              <h3 className="mt-1 text-2xl font-semibold text-[color:var(--text-primary)]">
                {group.name}
              </h3>
            </div>
          </div>
          <span
            className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase ${group.statusClass}`}
          >
            {group.status}
          </span>
        </div>

        <p className="mt-6 max-w-xl text-sm leading-7 text-[color:var(--text-muted)]">
          {group.description}
        </p>

        <div className="mt-6 grid gap-2 sm:grid-cols-2">
          {group.items.map((item) => (
            <div
              key={item}
              className="flex items-center gap-3 rounded-lg border border-[color:var(--border)] bg-black/20 px-3 py-3"
            >
              <Check className="h-4 w-4 shrink-0 text-cyan-300" />
              <span className="text-sm font-medium text-[color:var(--text-secondary)]">
                {item}
              </span>
            </div>
          ))}
        </div>

        <a
          href={group.ctaHref}
          className="mt-7 inline-flex h-11 items-center gap-2 rounded-full border border-[color:var(--border)] px-5 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[var(--surface-strong)]"
        >
          {group.ctaLabel}
          <ArrowRight className="h-4 w-4" />
        </a>
      </div>
    </article>
  );
}

function IconCard({
  item,
}: {
  item: {
    icon: LucideIcon;
    title: string;
    detail: string;
  };
}) {
  const Icon = item.icon;

  return (
    <article className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-6">
      <Icon className="h-5 w-5 text-emerald-300" />
      <h3 className="mt-5 text-lg font-semibold text-[color:var(--text-primary)]">
        {item.title}
      </h3>
      <p className="mt-3 text-sm leading-7 text-[color:var(--text-muted)]">{item.detail}</p>
    </article>
  );
}
