import {
  CheckCircle2,
  ChevronDown,
  Database,
  FileJson,
  GitBranch,
  Layers3,
  Rows3,
  ShieldCheck,
  Sparkles,
  Table2,
} from "lucide-react";
import Link from "next/link";

import type { DemoWorkspace } from "@/data/demo-workspaces";

export function DemoWorkspaceDashboard({ workspace }: { workspace: DemoWorkspace }) {
  const isDocument = workspace.kind === "document";
  const isPlanned = workspace.kind === "planned";

  return (
    <section className="mx-auto max-w-[1760px] px-3 py-5 sm:px-6 sm:py-8 lg:px-8 xl:px-10">
      <div className="overflow-hidden rounded-xl border border-cyan-300/10 bg-[#050917] shadow-[0_24px_90px_rgba(0,0,0,0.38)]">
        <div className="grid min-w-0 xl:grid-cols-[17rem_minmax(0,1fr)]">
          <DemoExplorer workspace={workspace} />

          <main className="min-w-0 border-t border-cyan-300/10 bg-[#080d1b] text-zinc-100 xl:border-l xl:border-t-0">
            <DemoHeader workspace={workspace} />
            <DemoResourceBar workspace={workspace} />
            <div className="workspace-scrollbar-dark min-h-[32rem] max-h-[44rem] overflow-auto bg-[#080d1b]">
              {isPlanned ? (
                <PlannedDemo workspace={workspace} />
              ) : isDocument ? (
                <DocumentDemo workspace={workspace} />
              ) : (
                <TableDemo workspace={workspace} />
              )}
            </div>
            <DemoQualityBar workspace={workspace} />
          </main>
        </div>
      </div>
    </section>
  );
}

function DemoExplorer({ workspace }: { workspace: DemoWorkspace }) {
  const ResourceIcon = workspace.kind === "document" ? FileJson : workspace.kind === "graph" ? GitBranch : Table2;

  return (
    <aside className="bg-[#060a16] text-zinc-100">
      <details className="group" open>
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 border-b border-cyan-300/10 px-4 py-4 marker:hidden">
          <div className="min-w-0">
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-zinc-500">
              Demo source
            </p>
            <p className="mt-1 truncate text-sm font-semibold text-white">{workspace.database}</p>
          </div>
          <ChevronDown className="h-4 w-4 shrink-0 text-zinc-500 transition group-open:rotate-180" />
        </summary>

        <div className="grid gap-4 p-4 sm:grid-cols-2 xl:grid-cols-1">
          <section className="rounded-lg border border-emerald-300/15 bg-emerald-300/[0.07] p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 text-xs font-semibold text-emerald-100">
                <span className="h-2 w-2 rounded-full bg-emerald-300" />
                Connected
              </span>
              <span className="text-[0.68rem] font-semibold uppercase text-emerald-200/60">
                {workspace.locale}
              </span>
            </div>
            <p className="mt-3 truncate text-xs font-semibold text-zinc-200">{workspace.engine}</p>
            <p className="mt-1 truncate text-xs text-zinc-500">{workspace.schema}</p>
          </section>

          <section>
            <div className="flex items-center justify-between px-1">
              <span className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-zinc-500">
                {resourceLabel(workspace)}
              </span>
              <span className="text-xs text-zinc-600">{workspace.resources.length}</span>
            </div>
            <div className="mt-2 space-y-1.5">
              {workspace.resources.map((resource, index) => (
                <div
                  key={resource.name}
                  className={`flex h-10 items-center justify-between gap-2 rounded-lg px-2.5 text-sm ${
                    index === 0
                      ? "bg-cyan-300/15 text-cyan-100 ring-1 ring-cyan-300/25"
                      : "text-zinc-400"
                  }`}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <ResourceIcon className="h-4 w-4 shrink-0" />
                    <span className="truncate">{resource.name}</span>
                  </span>
                  <span className="shrink-0 text-xs font-semibold text-zinc-500">
                    {resource.count.toLocaleString()}
                  </span>
                </div>
              ))}
              {workspace.resources.length === 0 ? (
                <p className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-xs leading-5 text-zinc-500">
                  Scheduled for a later phase.
                </p>
              ) : null}
            </div>
          </section>
        </div>
      </details>

      <div className="border-t border-white/[0.06] p-4">
        <Link
          href="/demos"
          className="inline-flex h-10 w-full items-center justify-center rounded-lg border border-white/10 text-sm font-semibold text-zinc-300 transition hover:border-cyan-300/30 hover:text-cyan-100"
        >
          All demos
        </Link>
      </div>
    </aside>
  );
}

function DemoHeader({ workspace }: { workspace: DemoWorkspace }) {
  const Icon =
    workspace.kind === "document"
      ? FileJson
      : workspace.kind === "graph"
        ? GitBranch
        : workspace.kind === "planned"
          ? Sparkles
          : Database;

  return (
    <header className="border-b border-cyan-300/10 px-4 py-5 sm:px-5">
      <div className="flex flex-col gap-5 2xl:flex-row 2xl:items-center 2xl:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-cyan-300/20 bg-cyan-300/10 text-cyan-100">
              <Icon className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-semibold text-white sm:text-2xl">{workspace.name}</h1>
                {workspace.kind !== "planned" ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-300" aria-label="Validated" />
                ) : null}
              </div>
              <p className="mt-1 truncate text-xs text-zinc-500 sm:text-sm">
                {workspace.database} · {workspace.schema} · {workspace.locale}
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 2xl:w-[34rem]">
          <DemoMetric icon={Rows3} label="Records" value={workspace.rows.toLocaleString()} />
          <DemoMetric icon={Layers3} label={resourceLabel(workspace)} value={String(workspace.resources.length)} />
          <DemoMetric icon={Table2} label="Fields" value={String(workspace.columns)} />
          <DemoMetric icon={ShieldCheck} label="Validation" value={workspace.kind === "planned" ? "Planned" : "Passed"} />
        </div>
      </div>
    </header>
  );
}

function DemoResourceBar({ workspace }: { workspace: DemoWorkspace }) {
  const resource = workspace.resources[0];
  const view = workspace.kind === "document" ? "JSON documents" : workspace.kind === "graph" ? "Node preview" : "Table preview";

  return (
    <div className="flex min-h-16 flex-col gap-2 border-b border-white/[0.07] px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="truncate text-base font-semibold text-white sm:text-lg">
            {resource?.name ?? workspace.name}
          </h2>
          {resource ? (
            <span className="rounded-md bg-white/[0.06] px-2 py-1 text-xs font-semibold text-zinc-400">
              {resource.count.toLocaleString()} records
            </span>
          ) : null}
        </div>
        <p className="mt-1 truncate text-xs text-zinc-500">{workspace.description}</p>
      </div>
      <span className="shrink-0 text-xs font-semibold uppercase tracking-[0.12em] text-cyan-200">
        {view}
      </span>
    </div>
  );
}

function TableDemo({ workspace }: { workspace: DemoWorkspace }) {
  return (
    <div className="workspace-scrollbar-dark min-h-full overflow-auto">
      <table className="min-w-[1080px] border-separate border-spacing-0 text-left text-sm">
        <thead className="sticky top-0 z-10 bg-[#101727] shadow-[0_1px_0_rgba(255,255,255,0.08)]">
          <tr>
            <th className="w-14 border-b border-r border-white/10 px-3 py-3 text-xs font-semibold text-zinc-500">
              #
            </th>
            {workspace.tableColumns.map((column) => (
              <th
                key={column}
                className="min-w-36 border-b border-r border-white/10 px-3 py-3 align-bottom"
              >
                <span className="block text-sm font-semibold text-zinc-100">{column}</span>
                <span className="mt-1 block text-[0.68rem] font-semibold uppercase text-zinc-500">
                  {column === "id" ? "identifier" : "text"}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {workspace.tableRows.map((row, index) => (
            <tr
              key={row.id ?? String(index)}
              className={`${(index + 1) % 2 === 0 ? "bg-white/[0.045]" : "bg-transparent"} hover:bg-cyan-300/[0.08]`}
            >
              <td className="border-b border-r border-white/[0.06] px-3 py-3 text-xs font-semibold text-zinc-500">
                {index + 1}
              </td>
              {workspace.tableColumns.map((column) => (
                <td
                  key={column}
                  className="max-w-72 truncate border-b border-r border-white/[0.06] px-3 py-3 text-zinc-300"
                >
                  {column === "status" || column === "risk_band" ? (
                    <span className={`rounded-md px-2 py-1 text-xs font-semibold ${demoStatusClass(row[column])}`}>
                      {row[column]}
                    </span>
                  ) : (
                    row[column]
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DocumentDemo({ workspace }: { workspace: DemoWorkspace }) {
  return (
    <div className="grid gap-3 p-4 lg:grid-cols-2 2xl:grid-cols-3">
      {workspace.documents.map((document, index) => (
        <article key={String(document._id ?? index)} className="min-w-0 rounded-lg border border-white/10 bg-white/[0.035]">
          <div className="flex items-center justify-between border-b border-white/10 px-3 py-2">
            <p className="text-xs font-semibold text-zinc-300">Customer {index + 1}</p>
            <p className="text-[0.68rem] font-semibold uppercase text-zinc-600">JSON</p>
          </div>
          <pre className="workspace-scrollbar-dark max-h-80 overflow-auto p-3 text-xs leading-5 text-zinc-300">
            {JSON.stringify(document, null, 2)}
          </pre>
        </article>
      ))}
    </div>
  );
}

function PlannedDemo({ workspace }: { workspace: DemoWorkspace }) {
  return (
    <div className="grid min-h-[32rem] place-items-center px-6 text-center">
      <div className="max-w-lg">
        <Sparkles className="mx-auto h-9 w-9 text-zinc-600" />
        <p className="mt-4 text-lg font-semibold text-white">{workspace.name}</p>
        <p className="mt-2 text-sm leading-6 text-zinc-500">{workspace.description}</p>
      </div>
    </div>
  );
}

function DemoQualityBar({ workspace }: { workspace: DemoWorkspace }) {
  return (
    <footer className="grid gap-px border-t border-white/[0.07] bg-white/[0.07] sm:grid-cols-3">
      <QualityItem label="Locale" value={workspace.locale} />
      <QualityItem label="Generation" value="Deterministic seed" />
      <QualityItem label="Integrity" value={workspace.kind === "planned" ? "Policy planned" : "Validated output"} />
    </footer>
  );
}

function DemoMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Rows3;
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-0 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-[0.66rem] font-semibold uppercase text-zinc-500">{label}</p>
        <Icon className="h-3.5 w-3.5 shrink-0 text-cyan-300" />
      </div>
      <p className="mt-1 truncate text-base font-semibold text-white">{value}</p>
    </div>
  );
}

function QualityItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 bg-[#060a16] px-4 py-3 text-xs">
      <span className="font-semibold uppercase tracking-[0.1em] text-zinc-600">{label}</span>
      <span className="font-semibold text-zinc-300">{value}</span>
    </div>
  );
}

function resourceLabel(workspace: DemoWorkspace) {
  if (workspace.kind === "document") return "Collections";
  if (workspace.kind === "graph") return "Graph sets";
  return "Tables";
}

function demoStatusClass(status = "") {
  if (status === "active" || status === "low") {
    return "border border-emerald-300/20 bg-emerald-300/10 text-emerald-100";
  }
  if (status === "pending" || status === "medium") {
    return "border border-amber-300/20 bg-amber-300/10 text-amber-100";
  }
  if (status === "review" || status === "high") {
    return "border border-red-300/20 bg-red-300/10 text-red-100";
  }
  return "border border-white/10 bg-white/[0.06] text-zinc-300";
}
