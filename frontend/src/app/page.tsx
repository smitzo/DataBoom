import {
  Activity,
  ArrowRight,
  BadgeCheck,
  Banknote,
  Blocks,
  Braces,
  CheckCircle2,
  Cpu,
  Database,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  GitBranch,
  HeartPulse,
  KeyRound,
  Play,
  Server,
  ShieldCheck,
  Sparkles,
  Workflow,
  X,
} from "lucide-react";
import type { ComponentType, ReactNode } from "react";

const navItems = ["Platform", "Profiles", "Pipeline", "Validation", "Demos"];

const heroMetrics = [
  { label: "Benchmark", value: "100k rows", tone: "text-emerald-300" },
  { label: "Memory", value: "50.7 MB", tone: "text-sky-300" },
  { label: "Exports", value: "CSV JSON SQL", tone: "text-amber-200" },
];

const profiles = [
  {
    name: "Financial",
    role: "Banking and fintech data",
    description: "Customers, accounts, balances, merchants, currencies, and transactions.",
    tags: ["accounts", "transactions"],
    icon: Banknote,
    selected: true,
    tone: "border-emerald-300/40 text-emerald-200",
  },
  {
    name: "Healthcare",
    role: "Patient and clinical data",
    description: "Patients, encounters, vitals, diagnosis codes, and insurance values.",
    tags: ["patients", "vitals"],
    icon: HeartPulse,
    selected: false,
    tone: "border-rose-300/40 text-rose-200",
  },
  {
    name: "General",
    role: "Schema-first fallback",
    description: "Typed fake values for tables that do not need a domain overlay.",
    tags: ["schema", "generic"],
    icon: Blocks,
    selected: false,
    tone: "border-sky-300/40 text-sky-200",
  },
];

const pipeline = [
  { label: "Schema parsing", detail: "PostgreSQL DDL", icon: Database },
  { label: "Relationship graph", detail: "FK-aware ordering", icon: GitBranch },
  { label: "Domain values", detail: "Profile overlays", icon: Sparkles },
  { label: "Streaming export", detail: "Local artifacts", icon: Download },
  { label: "Validation", detail: "Keys and manifest", icon: ShieldCheck },
  { label: "Benchmarking", detail: "100k baseline", icon: Activity },
];

const formats = [
  { name: "CSV", icon: FileSpreadsheet, state: "ready" },
  { name: "JSON", icon: FileJson, state: "ready" },
  { name: "SQL", icon: FileText, state: "ready" },
];

const demos = [
  {
    name: "Financial demo",
    tables: "customers, bank_accounts, transactions",
    rows: "1,100 rows",
    tone: "border-emerald-300/30",
  },
  {
    name: "Healthcare demo",
    tables: "patients, encounters, vitals",
    rows: "1,300 rows",
    tone: "border-rose-300/30",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <Announcement />
      <Header />

      <section id="platform" className="relative overflow-hidden border-b border-white/10">
        <div className="absolute inset-y-0 right-0 hidden w-1/2 bg-gradient-to-l from-zinc-800/35 to-transparent lg:block" />
        <div className="mx-auto grid min-h-[760px] max-w-[1680px] gap-10 px-5 py-12 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-12 xl:px-16">
          <div className="relative z-10 max-w-3xl">
            <div className="flex flex-wrap items-center gap-3">
              <span className="h-2 w-2 rounded-full bg-white shadow-[0_0_16px_rgba(255,255,255,0.85)]" />
              <span className="text-sm font-medium uppercase text-zinc-400">
                Open-source synthetic data engine
              </span>
              <span className="rounded-md border border-emerald-300/40 bg-emerald-300/10 px-3 py-1 text-xs font-semibold uppercase text-emerald-200">
                Phase 1 ready
              </span>
            </div>

            <h1 className="mt-9 text-5xl font-semibold leading-none text-white sm:text-6xl lg:text-7xl">
              One engine to generate{" "}
              <span className="font-serif italic text-zinc-300">domain-aware</span>{" "}
              relational data.
            </h1>

            <div className="mt-8 max-w-2xl border-l border-white/20 pl-5">
              <p className="text-xl font-semibold leading-8 text-white">
                Boom Data turns PostgreSQL schemas into validated CSV, JSON, and SQL
                artifacts for fintech, healthcare, and customer-sensitive workflows.
              </p>
            </div>

            <p className="mt-6 max-w-2xl text-base leading-7 text-zinc-400">
              The backend already handles schema parsing, dependency ordering,
              deterministic generation, local exports, and validation reports.
              Use it to create high-volume demo, test, and analytics datasets
              without asking an LLM to stream every row.
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              <button className="inline-flex h-12 items-center gap-2 rounded-md bg-white px-6 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-100">
                <Play className="h-4 w-4" />
                Run generation
              </button>
              <a
                href="#profiles"
                className="inline-flex h-12 items-center gap-2 rounded-md border border-white/15 px-6 text-sm font-semibold text-white transition hover:border-white/35"
              >
                See profiles
                <ArrowRight className="h-4 w-4" />
              </a>
            </div>

            <div className="mt-12 grid gap-3 sm:grid-cols-3">
              {heroMetrics.map((metric) => (
                <MetricTile key={metric.label} {...metric} />
              ))}
            </div>
          </div>

          <ControlCenter />
        </div>
      </section>

      <Section
        id="profiles"
        eyebrow="Domain profiles"
        title="Use-case focused generators, not one generic blob."
        subtitle="The core engine stays schema-first. Profiles add realistic values only where the domain benefits from them."
      >
        <div className="grid gap-4 lg:grid-cols-3">
          {profiles.map((profile) => (
            <ProfileCard key={profile.name} {...profile} />
          ))}
        </div>
      </Section>

      <Section
        id="pipeline"
        eyebrow="Engine pipeline"
        title="Built around relationships, exports, and validation."
        subtitle="The UI mirrors the backend architecture so every future API endpoint has a natural place to land."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {pipeline.map((step) => (
            <PipelineCard key={step.label} {...step} />
          ))}
        </div>
      </Section>

      <Section
        id="validation"
        eyebrow="Validation snapshot"
        title="Current baseline is visible by default."
        subtitle="Phase 1 generated and validated a 100k-record benchmark with local artifacts."
      >
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <ValidationMetric label="Records" value="100k" icon={Database} />
          <ValidationMetric label="Elapsed" value="44.7s" icon={Cpu} />
          <ValidationMetric label="Peak memory" value="50.7 MB" icon={Server} />
          <ValidationMetric label="Status" value="Passed" icon={CheckCircle2} success />
        </div>
      </Section>

      <Section
        id="demos"
        eyebrow="Demo data"
        title="Checked-in datasets for product demos and regression checks."
        subtitle="Financial and healthcare CSVs are already generated through the backend engine."
      >
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr_0.9fr]">
          {demos.map((demo) => (
            <DemoDataset key={demo.name} {...demo} />
          ))}
          <ArtifactPanel />
        </div>
      </Section>
    </main>
  );
}

function Announcement() {
  return (
    <div className="bg-gradient-to-r from-indigo-700 via-zinc-900 to-red-600">
      <div className="mx-auto flex h-10 max-w-[1680px] items-center justify-between gap-4 px-5 text-sm text-white sm:px-8 lg:px-12 xl:px-16">
        <div className="flex min-w-0 items-center gap-3">
          <span className="rounded-md bg-white/15 px-2 py-1 text-xs font-semibold">NEW</span>
          <span className="truncate font-medium">
            Phase 1 backend now supports domain profiles, JSON export, demos, and validation.
          </span>
        </div>
        <X className="h-4 w-4 shrink-0 text-white/80" />
      </div>
    </div>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-black/95 backdrop-blur">
      <div className="mx-auto flex h-20 max-w-[1680px] items-center justify-between gap-5 px-5 sm:px-8 lg:px-12 xl:px-16">
        <a href="#platform" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-zinc-950 text-emerald-300 ring-1 ring-white/10">
            <Database className="h-5 w-5" />
          </span>
          <span className="text-sm font-semibold uppercase text-white">Boom Data</span>
        </a>

        <nav className="hidden items-center gap-2 lg:flex">
          {navItems.map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase()}`}
              className="rounded-md px-3 py-2 text-sm font-medium text-zinc-400 transition hover:bg-white/5 hover:text-white"
            >
              {item}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <span className="inline-flex h-9 items-center gap-2 rounded-md border border-white/10 px-3 text-xs font-semibold uppercase text-zinc-400">
            <KeyRound className="h-3.5 w-3.5" />
            Local first
          </span>
          <button className="inline-flex h-11 items-center rounded-full bg-white px-6 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-100">
            Run locally
          </button>
        </div>
      </div>
    </header>
  );
}

function ControlCenter() {
  return (
    <div className="relative z-10 lg:pl-4 xl:pl-10">
      <div className="rounded-lg border border-white/15 bg-zinc-950/95 shadow-2xl shadow-black">
        <div className="flex h-12 items-center justify-between border-b border-white/10 px-5">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-zinc-700" />
            <span className="h-3 w-3 rounded-full bg-zinc-700" />
            <span className="h-3 w-3 rounded-full bg-zinc-700" />
          </div>
          <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 py-1 text-xs font-medium text-emerald-200">
            Run Control Center
          </span>
        </div>

        <div className="grid min-h-[520px] lg:grid-cols-[220px_1fr]">
          <aside className="hidden border-r border-white/10 p-5 lg:block">
            <p className="text-xs font-semibold uppercase text-zinc-600">Navigation</p>
            <div className="mt-5 space-y-2">
              <MockNavItem icon={Database} label="Dashboard" active />
              <MockNavItem icon={Workflow} label="Generation" />
              <MockNavItem icon={GitBranch} label="Relationships" />
              <MockNavItem icon={Download} label="Artifacts" />
              <MockNavItem icon={ShieldCheck} label="Validation" />
            </div>
            <div className="mt-12 rounded-lg border border-white/10 bg-white/[0.03] p-4">
              <p className="text-xs font-semibold uppercase text-zinc-500">System status</p>
              <div className="mt-4 flex items-center justify-between gap-3">
                <span className="text-sm text-zinc-300">Local disk</span>
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
              </div>
            </div>
          </aside>

          <div className="p-5 sm:p-6">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <p className="text-2xl font-semibold text-white">Synthetic Data Run</p>
                <p className="mt-2 text-sm text-zinc-500">PostgreSQL schema to local artifacts</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusPill label="Financial profile" color="blue" />
                <StatusPill label="Validation on" color="green" />
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <ControlMetric label="Rows planned" value="100,000" hint="+ deterministic seed" />
              <ControlMetric label="Tables" value="3" hint="parent-first graph" />
              <ControlMetric label="Artifacts" value="3" hint="csv json sql" />
            </div>

            <div className="mt-7 grid gap-4 xl:grid-cols-[1fr_0.8fr]">
              <div className="rounded-lg border border-indigo-400/35 bg-indigo-500/10 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold text-white">Relationship plan</p>
                    <p className="mt-1 text-sm text-zinc-400">Parent rows feed child keys.</p>
                  </div>
                  <GitBranch className="h-5 w-5 text-indigo-300" />
                </div>
                <div className="mt-5 space-y-3">
                  <PlanRow step="01" label="customers" detail="primary table" />
                  <PlanRow step="02" label="bank_accounts" detail="customer_id resolved" />
                  <PlanRow step="03" label="transactions" detail="account_id resolved" />
                </div>
              </div>

              <div className="rounded-lg border border-amber-400/30 bg-amber-500/10 p-5">
                <p className="font-semibold text-white">Export queue</p>
                <div className="mt-5 space-y-3">
                  {formats.map((format) => (
                    <FormatRow key={format.name} {...format} />
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-4 rounded-lg border border-emerald-300/25 bg-emerald-300/10 p-4">
              <div className="flex items-center gap-3">
                <BadgeCheck className="h-5 w-5 text-emerald-300" />
                <p className="text-sm font-semibold text-emerald-100">
                  Latest validation passed for primary keys, foreign keys, manifest, and artifacts.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({
  id,
  eyebrow,
  title,
  subtitle,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="border-b border-white/10 bg-black">
      <div className="mx-auto max-w-[1680px] px-5 py-16 sm:px-8 lg:px-12 xl:px-16">
        <div className="grid gap-8 xl:grid-cols-[0.42fr_1fr]">
          <div>
            <p className="text-sm font-semibold uppercase text-zinc-500">{eyebrow}</p>
            <h2 className="mt-5 max-w-xl text-3xl font-semibold leading-tight text-white lg:text-5xl">
              {title}
            </h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-zinc-400">{subtitle}</p>
          </div>
          <div>{children}</div>
        </div>
      </div>
    </section>
  );
}

function MetricTile({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
      <p className="text-sm text-zinc-500">{label}</p>
      <p className={`mt-2 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

function MockNavItem({
  icon: Icon,
  label,
  active = false,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  active?: boolean;
}) {
  return (
    <div
      className={`flex h-10 items-center gap-3 rounded-md px-3 text-sm ${
        active ? "bg-indigo-500/20 text-white" : "text-zinc-500"
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </div>
  );
}

function StatusPill({ label, color }: { label: string; color: "blue" | "green" }) {
  const className =
    color === "green"
      ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-200"
      : "border-indigo-300/25 bg-indigo-300/10 text-indigo-200";

  return (
    <span className={`rounded-md border px-3 py-2 text-xs font-semibold ${className}`}>
      {label}
    </span>
  );
}

function ControlMetric({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
      <p className="text-xs font-semibold uppercase text-zinc-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm text-emerald-300">{hint}</p>
    </div>
  );
}

function PlanRow({ step, label, detail }: { step: string; label: string; detail: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md bg-black/30 px-3 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <span className="text-xs font-semibold text-indigo-300">{step}</span>
        <span className="truncate text-sm font-medium text-white">{label}</span>
      </div>
      <span className="text-right text-xs text-zinc-500">{detail}</span>
    </div>
  );
}

function FormatRow({
  name,
  icon: Icon,
  state,
}: {
  name: string;
  icon: ComponentType<{ className?: string }>;
  state: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-white/10 bg-black/25 px-4 py-3">
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-amber-200" />
        <span className="text-sm font-medium text-white">{name}</span>
      </div>
      <span className="text-xs font-medium uppercase text-zinc-500">{state}</span>
    </div>
  );
}

function ProfileCard({
  name,
  role,
  description,
  tags,
  icon: Icon,
  selected,
  tone,
}: {
  name: string;
  role: string;
  description: string;
  tags: string[];
  icon: ComponentType<{ className?: string }>;
  selected: boolean;
  tone: string;
}) {
  return (
    <button className={`min-h-72 rounded-lg border bg-white/[0.03] p-5 text-left transition hover:bg-white/[0.05] ${tone}`}>
      <div className="flex items-start justify-between gap-4">
        <span className="flex h-10 w-10 items-center justify-center rounded-md bg-white/5">
          <Icon className="h-5 w-5" />
        </span>
        {selected ? <BadgeCheck className="h-5 w-5 text-emerald-300" /> : null}
      </div>
      <p className="mt-6 text-lg font-semibold text-white">{name}</p>
      <p className="mt-1 text-sm font-semibold uppercase text-current">{role}</p>
      <p className="mt-4 text-sm leading-6 text-zinc-400">{description}</p>
      <div className="mt-6 flex flex-wrap gap-2">
        {tags.map((tag) => (
          <span key={tag} className="rounded-md border border-white/10 px-2 py-1 text-xs uppercase text-zinc-500">
            {tag}
          </span>
        ))}
      </div>
    </button>
  );
}

function PipelineCard({
  label,
  detail,
  icon: Icon,
}: {
  label: string;
  detail: string;
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
      <Icon className="h-5 w-5 text-indigo-300" />
      <p className="mt-5 font-semibold text-white">{label}</p>
      <p className="mt-2 text-sm text-zinc-500">{detail}</p>
    </div>
  );
}

function ValidationMetric({
  label,
  value,
  icon: Icon,
  success = false,
}: {
  label: string;
  value: string;
  icon: ComponentType<{ className?: string }>;
  success?: boolean;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-zinc-500">{label}</p>
        <Icon className={success ? "h-5 w-5 text-emerald-300" : "h-5 w-5 text-zinc-500"} />
      </div>
      <p className={success ? "mt-5 text-2xl font-semibold text-emerald-300" : "mt-5 text-2xl font-semibold text-white"}>
        {value}
      </p>
    </div>
  );
}

function DemoDataset({
  name,
  tables,
  rows,
  tone,
}: {
  name: string;
  tables: string;
  rows: string;
  tone: string;
}) {
  return (
    <div className={`rounded-lg border bg-white/[0.03] p-5 ${tone}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-lg font-semibold text-white">{name}</p>
          <p className="mt-3 text-sm leading-6 text-zinc-400">{tables}</p>
        </div>
        <BadgeCheck className="h-5 w-5 text-emerald-300" />
      </div>
      <p className="mt-8 text-sm font-semibold text-zinc-100">{rows}</p>
    </div>
  );
}

function ArtifactPanel() {
  return (
    <div className="rounded-lg border border-amber-300/25 bg-amber-400/10 p-5">
      <p className="text-lg font-semibold text-white">Output formats</p>
      <p className="mt-3 text-sm leading-6 text-zinc-400">
        The engine can export the same run into multiple local artifact types for
        analysts, backend tests, and database loading.
      </p>
      <div className="mt-6 space-y-3">
        {formats.map((format) => (
          <FormatRow key={format.name} {...format} />
        ))}
      </div>
    </div>
  );
}
