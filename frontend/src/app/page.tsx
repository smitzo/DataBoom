import {
  Activity,
  ArrowRight,
  BadgeCheck,
  Banknote,
  Blocks,
  Braces,
  CheckCircle2,
  Database,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  HeartPulse,
  Play,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { ComponentType, ReactNode } from "react";

const navItems = ["Builder", "Domains", "Pipeline", "Validation", "Demos"];

const metrics = [
  { label: "Benchmark", value: "100k rows", tone: "text-emerald-300" },
  { label: "Peak memory", value: "50.7 MB", tone: "text-sky-300" },
  { label: "Artifacts", value: "CSV JSON SQL", tone: "text-amber-200" },
];

const domains = [
  {
    name: "Financial",
    description: "Banking customers, accounts, balances, currencies, and transactions.",
    detail: "Demo dataset: 1,100 rows",
    icon: Banknote,
    selected: true,
    tone: "border-emerald-300/50 bg-emerald-300/10 text-emerald-200",
  },
  {
    name: "Healthcare",
    description: "Patients, encounters, vitals, diagnosis codes, and insurance values.",
    detail: "Demo dataset: 1,300 rows",
    icon: HeartPulse,
    selected: false,
    tone: "border-rose-300/40 bg-rose-300/10 text-rose-200",
  },
  {
    name: "General",
    description: "Schema-first values for tables without a domain-specific profile.",
    detail: "Fallback profile",
    icon: Blocks,
    selected: false,
    tone: "border-sky-300/40 bg-sky-300/10 text-sky-200",
  },
];

const formats = [
  { name: "CSV", icon: FileSpreadsheet, state: "Ready" },
  { name: "JSON", icon: FileJson, state: "Ready" },
  { name: "SQL", icon: FileText, state: "Ready" },
];

const pipeline = [
  "Parse PostgreSQL schema",
  "Build relationship graph",
  "Plan parent-first generation",
  "Generate deterministic values",
  "Stream export artifacts",
  "Validate keys and manifest",
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
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <Header />

      <section id="builder" className="mx-auto max-w-6xl px-5 py-10 sm:px-8 lg:py-14">
        <div className="grid gap-8 lg:grid-cols-5 lg:items-start">
          <div className="lg:col-span-3">
            <div className="inline-flex items-center gap-2 rounded-md border border-emerald-300/30 bg-emerald-300/10 px-3 py-2 text-sm font-medium text-emerald-200">
              <ShieldCheck className="h-4 w-4" />
              Phase 1 engine
            </div>
            <h1 className="mt-6 max-w-3xl text-4xl font-semibold text-white sm:text-5xl">
              Generate relational synthetic data.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-300">
              PostgreSQL schema in, validated local artifacts out. Built for
              high-volume relational runs with deterministic output and
              domain-aware values.
            </p>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {metrics.map((metric) => (
                <MetricTile key={metric.label} {...metric} />
              ))}
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <button className="inline-flex h-11 items-center gap-2 rounded-md bg-white px-5 text-sm font-semibold text-zinc-950 shadow-lg shadow-emerald-950/20 transition hover:bg-emerald-100">
                <Play className="h-4 w-4" />
                Run generation
              </button>
              <a
                href="#domains"
                className="inline-flex h-11 items-center gap-2 rounded-md border border-white/10 px-5 text-sm font-semibold text-zinc-100 transition hover:border-white/25"
              >
                View profiles
                <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </div>

          <RunSetup />
        </div>
      </section>

      <Section id="domains" title="Domain Profiles" subtitle="Use-case specific value layers.">
        <div className="grid gap-4 md:grid-cols-3">
          {domains.map((domain) => (
            <DomainProfile key={domain.name} {...domain} />
          ))}
        </div>
      </Section>

      <Section id="pipeline" title="Pipeline And Exports" subtitle="The engine path from schema to artifacts.">
        <div className="grid gap-8 lg:grid-cols-2">
          <div className="space-y-3">
            {pipeline.map((step, index) => (
              <PipelineStep key={step} index={index + 1} label={step} />
            ))}
          </div>

          <div className="rounded-lg border border-white/10 bg-zinc-950/70 p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-white">Artifact targets</p>
                <p className="mt-1 text-sm text-zinc-400">Local disk for Phase 1 and 2.</p>
              </div>
              <Download className="h-5 w-5 text-amber-200" />
            </div>
            <div className="mt-5 space-y-3">
              {formats.map((format) => (
                <FormatRow key={format.name} {...format} />
              ))}
            </div>
          </div>
        </div>
      </Section>

      <Section id="validation" title="Validation Snapshot" subtitle="Latest local benchmark result.">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <ValidationMetric label="Records" value="100k" />
          <ValidationMetric label="Elapsed" value="44.7s" />
          <ValidationMetric label="Peak memory" value="50.7 MB" />
          <ValidationMetric label="Status" value="Passed" success />
        </div>
      </Section>

      <Section id="demos" title="Demo Datasets" subtitle="Checked-in CSV examples generated by the backend.">
        <div className="grid gap-4 md:grid-cols-2">
          {demos.map((demo) => (
            <DemoDataset key={demo.name} {...demo} />
          ))}
        </div>
      </Section>
    </main>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-zinc-950/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5 sm:px-8">
        <a href="#builder" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-400 text-zinc-950">
            <Database className="h-5 w-5" />
          </span>
          <span>
            <span className="block text-sm font-semibold text-white">Boom Data</span>
            <span className="block text-xs text-zinc-400">Synthetic data workbench</span>
          </span>
        </a>

        <nav className="hidden items-center gap-1 md:flex">
          {navItems.map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase()}`}
              className="rounded-md px-3 py-2 text-sm font-medium text-zinc-300 transition hover:bg-white/5 hover:text-white"
            >
              {item}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}

function RunSetup() {
  return (
    <aside className="rounded-lg border border-white/10 bg-white/[0.04] p-5 shadow-2xl shadow-black/30 lg:col-span-2">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-white">Run setup</p>
          <p className="mt-1 text-sm text-zinc-400">Financial profile, local export.</p>
        </div>
        <Activity className="h-5 w-5 text-emerald-300" />
      </div>

      <div className="mt-5 divide-y divide-white/10">
        <SetupRow icon={Database} label="Schema" value="PostgreSQL DDL" />
        <SetupRow icon={Banknote} label="Profile" value="Financial" />
        <SetupRow icon={Braces} label="Rows" value="100k benchmark ready" />
        <SetupRow icon={Sparkles} label="Seed" value="demo-financial" />
      </div>

      <div className="mt-5 rounded-md border border-emerald-300/30 bg-emerald-300/10 px-3 py-3">
        <div className="flex items-center gap-2 text-sm font-medium text-emerald-100">
          <CheckCircle2 className="h-4 w-4" />
          Validation enabled
        </div>
      </div>
    </aside>
  );
}

function Section({
  id,
  title,
  subtitle,
  children,
}: {
  id: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="border-t border-white/10 bg-zinc-900/30">
      <div className="mx-auto max-w-6xl px-5 py-12 sm:px-8 lg:py-14">
        <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-white">{title}</h2>
            <p className="mt-2 text-sm text-zinc-400">{subtitle}</p>
          </div>
        </div>
        {children}
      </div>
    </section>
  );
}

function SetupRow({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-4">
      <div className="flex min-w-0 items-center gap-3">
        <Icon className="h-4 w-4 shrink-0 text-zinc-500" />
        <span className="text-sm text-zinc-400">{label}</span>
      </div>
      <span className="text-right text-sm font-medium text-white">{value}</span>
    </div>
  );
}

function MetricTile({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
      <p className="text-sm text-zinc-400">{label}</p>
      <p className={`mt-2 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

function DomainProfile({
  name,
  description,
  detail,
  icon: Icon,
  selected,
  tone,
}: {
  name: string;
  description: string;
  detail: string;
  icon: ComponentType<{ className?: string }>;
  selected: boolean;
  tone: string;
}) {
  return (
    <button className={`rounded-lg border p-5 text-left transition hover:border-white/30 ${tone}`}>
      <div className="flex items-start justify-between gap-4">
        <Icon className="h-6 w-6" />
        {selected ? <BadgeCheck className="h-5 w-5 text-emerald-300" /> : null}
      </div>
      <p className="mt-5 text-base font-semibold text-white">{name}</p>
      <p className="mt-2 text-sm leading-6 text-zinc-300">{description}</p>
      <p className="mt-4 text-sm font-medium">{detail}</p>
    </button>
  );
}

function PipelineStep({ index, label }: { index: number; label: string }) {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-zinc-800 text-sm font-semibold text-zinc-300">
        {index}
      </span>
      <span className="text-sm font-medium text-zinc-100">{label}</span>
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
    <div className="flex items-center justify-between gap-4 rounded-md border border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-sky-300" />
        <span className="text-sm font-medium text-white">{name}</span>
      </div>
      <span className="text-sm text-zinc-400">{state}</span>
    </div>
  );
}

function ValidationMetric({
  label,
  value,
  success = false,
}: {
  label: string;
  value: string;
  success?: boolean;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
      <p className="text-sm text-zinc-400">{label}</p>
      <p
        className={
          success
            ? "mt-2 text-xl font-semibold text-emerald-300"
            : "mt-2 text-xl font-semibold text-white"
        }
      >
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
    <div className={`rounded-lg border bg-zinc-950/60 p-5 ${tone}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-base font-semibold text-white">{name}</p>
          <p className="mt-2 text-sm leading-6 text-zinc-400">{tables}</p>
        </div>
        <BadgeCheck className="h-5 w-5 text-emerald-300" />
      </div>
      <p className="mt-5 text-sm font-semibold text-zinc-100">{rows}</p>
    </div>
  );
}
