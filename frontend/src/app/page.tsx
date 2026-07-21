import {
  Activity,
  ArrowRight,
  BadgeCheck,
  Banknote,
  Blocks,
  Braces,
  Database,
  FileJson,
  FileSpreadsheet,
  FileText,
  HeartPulse,
  Play,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { ComponentType } from "react";

const domains = [
  {
    name: "Financial",
    description: "Accounts, balances, currencies, merchants, and transactions.",
    icon: Banknote,
    active: true,
  },
  {
    name: "Healthcare",
    description: "Patients, encounters, diagnosis codes, vitals, and insurance.",
    icon: HeartPulse,
    active: false,
  },
  {
    name: "General",
    description: "Schema-first data when domain semantics are not required.",
    icon: Blocks,
    active: false,
  },
];

const formats = [
  { name: "CSV", icon: FileSpreadsheet, active: true },
  { name: "JSON", icon: FileJson, active: true },
  { name: "SQL", icon: FileText, active: false },
];

const demos = [
  {
    name: "Financial demo",
    tables: "customers, bank_accounts, transactions",
    rows: "1,100 rows",
    tone: "from-emerald-400/20 to-cyan-400/10",
  },
  {
    name: "Healthcare demo",
    tables: "patients, encounters, vitals",
    rows: "1,300 rows",
    tone: "from-rose-400/20 to-sky-400/10",
  },
];

const pipeline = [
  "Parse schema",
  "Plan rows",
  "Solve relationships",
  "Generate values",
  "Export artifacts",
  "Validate output",
];

export default function Home() {
  return (
    <main className="min-h-screen">
      <section className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-5 py-5 sm:px-8 lg:px-10">
        <header className="flex flex-col gap-4 border-b border-white/10 pb-5 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-emerald-400 text-zinc-950">
              <Database className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-emerald-300">
                Boom Data
              </p>
              <h1 className="text-2xl font-semibold text-white md:text-3xl">
                Synthetic data workbench
              </h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusPill icon={ShieldCheck} label="Validated CSVs" />
            <StatusPill icon={Activity} label="100k benchmark" />
            <button className="inline-flex h-10 items-center gap-2 rounded-md bg-white px-4 text-sm font-semibold text-zinc-950 shadow-lg shadow-emerald-950/20 transition hover:bg-emerald-100">
              <Play className="h-4 w-4" />
              Run generation
            </button>
          </div>
        </header>

        <section className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5 shadow-2xl shadow-black/30">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-medium text-emerald-300">
                  Phase 1 generator
                </p>
                <h2 className="mt-1 text-xl font-semibold text-white">
                  Configure a relational dataset
                </h2>
              </div>
              <div className="rounded-md border border-emerald-300/30 bg-emerald-300/10 px-3 py-2 text-xs font-medium text-emerald-100">
                Local disk artifacts
              </div>
            </div>

            <div className="mt-6 grid gap-5 md:grid-cols-3">
              <Field label="Schema source" value="PostgreSQL DDL" icon={Database} />
              <Field label="Default rows" value="10 per table" icon={Braces} />
              <Field label="Seed" value="demo-financial" icon={Sparkles} />
            </div>

            <div className="mt-6">
              <SectionLabel title="Domain profile" subtitle="Semantic value overlay" />
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {domains.map((domain) => (
                  <DomainCard key={domain.name} {...domain} />
                ))}
              </div>
            </div>

            <div className="mt-6">
              <SectionLabel title="Output formats" subtitle="Choose one or many" />
              <div className="mt-3 flex flex-wrap gap-3">
                {formats.map((format) => (
                  <FormatButton key={format.name} {...format} />
                ))}
              </div>
            </div>

            <div className="mt-6 rounded-lg border border-white/10 bg-zinc-950/70 p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-white">Generation plan</p>
                  <p className="mt-1 text-sm text-zinc-400">
                    Parent tables first, child rows choose valid foreign keys.
                  </p>
                </div>
                <ArrowRight className="h-5 w-5 text-emerald-300" />
              </div>
              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                {pipeline.map((step, index) => (
                  <div
                    key={step}
                    className="rounded-md border border-white/10 bg-white/[0.03] px-3 py-2"
                  >
                    <p className="text-xs text-zinc-500">0{index + 1}</p>
                    <p className="mt-1 text-sm font-medium text-zinc-100">{step}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <aside className="flex flex-col gap-5">
            <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
              <SectionLabel title="Validation summary" subtitle="Latest local benchmark" />
              <div className="mt-5 grid grid-cols-2 gap-3">
                <Metric label="Records" value="100k" />
                <Metric label="Peak memory" value="50.7 MB" />
                <Metric label="Elapsed" value="44.7s" />
                <Metric label="Status" value="Passed" success />
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
              <SectionLabel title="Demo datasets" subtitle="Generated through the engine" />
              <div className="mt-4 flex flex-col gap-3">
                {demos.map((demo) => (
                  <div
                    key={demo.name}
                    className={`rounded-lg border border-white/10 bg-gradient-to-br ${demo.tone} p-4`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-white">{demo.name}</p>
                        <p className="mt-1 text-sm text-zinc-300">{demo.tables}</p>
                      </div>
                      <BadgeCheck className="h-5 w-5 text-emerald-300" />
                    </div>
                    <p className="mt-3 text-sm font-medium text-zinc-100">{demo.rows}</p>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </section>
      </section>
    </main>
  );
}

function StatusPill({
  icon: Icon,
  label,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <div className="inline-flex h-10 items-center gap-2 rounded-md border border-white/10 bg-white/[0.04] px-3 text-sm text-zinc-200">
      <Icon className="h-4 w-4 text-emerald-300" />
      {label}
    </div>
  );
}

function Field({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-zinc-950/60 p-4">
      <Icon className="h-5 w-5 text-emerald-300" />
      <p className="mt-3 text-xs uppercase text-zinc-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

function SectionLabel({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <p className="text-sm font-semibold text-white">{title}</p>
      <p className="mt-1 text-sm text-zinc-400">{subtitle}</p>
    </div>
  );
}

function DomainCard({
  name,
  description,
  icon: Icon,
  active,
}: {
  name: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  active: boolean;
}) {
  return (
    <button
      className={`min-h-40 rounded-lg border p-4 text-left transition ${
        active
          ? "border-emerald-300/60 bg-emerald-300/10"
          : "border-white/10 bg-zinc-950/60 hover:border-white/25"
      }`}
    >
      <Icon className={active ? "h-6 w-6 text-emerald-300" : "h-6 w-6 text-zinc-400"} />
      <p className="mt-4 text-sm font-semibold text-white">{name}</p>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{description}</p>
    </button>
  );
}

function FormatButton({
  name,
  icon: Icon,
  active,
}: {
  name: string;
  icon: ComponentType<{ className?: string }>;
  active: boolean;
}) {
  return (
    <button
      className={`inline-flex h-10 items-center gap-2 rounded-md border px-4 text-sm font-medium transition ${
        active
          ? "border-cyan-300/60 bg-cyan-300/10 text-cyan-100"
          : "border-white/10 bg-zinc-950/60 text-zinc-300 hover:border-white/25"
      }`}
    >
      <Icon className="h-4 w-4" />
      {name}
    </button>
  );
}

function Metric({
  label,
  value,
  success = false,
}: {
  label: string;
  value: string;
  success?: boolean;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-zinc-950/60 p-4">
      <p className="text-xs uppercase text-zinc-500">{label}</p>
      <p
        className={
          success
            ? "mt-2 text-lg font-semibold text-emerald-300"
            : "mt-2 text-lg font-semibold text-white"
        }
      >
        {value}
      </p>
    </div>
  );
}
