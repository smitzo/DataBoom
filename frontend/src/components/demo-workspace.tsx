import {
  BarChart3,
  CheckCircle2,
  Database,
  Download,
  Eye,
  FileJson,
  Filter,
  GitBranch,
  Rows3,
  Search,
  Settings,
  Share2,
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
    <section className="mx-auto max-w-[1760px] px-5 py-8 sm:px-8 lg:px-12 xl:px-16">
      <div className="overflow-hidden rounded-2xl border border-cyan-300/10 bg-[#050917] shadow-[0_24px_90px_rgba(0,0,0,0.38)]">
        <div className="grid min-h-[calc(100vh-12rem)] lg:grid-cols-[18rem_minmax(0,1fr)_22rem]">
          <DemoExplorer workspace={workspace} />

          <main className="min-w-0 border-y border-cyan-300/10 bg-[#080d1b] text-zinc-100 lg:border-x lg:border-y-0">
            <DemoHeader workspace={workspace} />
            <DemoToolbar isDocument={isDocument} workspace={workspace} />
            <div className="workspace-scrollbar-dark h-[calc(100vh-27rem)] min-h-[34rem] overflow-auto bg-[#080d1b]">
              {isPlanned ? (
                <PlannedDemo workspace={workspace} />
              ) : isDocument ? (
                <DocumentDemo workspace={workspace} />
              ) : (
                <TableDemo workspace={workspace} />
              )}
            </div>
          </main>

          <DemoInspector workspace={workspace} />
        </div>
      </div>
    </section>
  );
}

function DemoExplorer({ workspace }: { workspace: DemoWorkspace }) {
  const ResourceIcon = workspace.kind === "document" ? FileJson : Table2;

  return (
    <aside className="bg-[#060a16] text-zinc-100">
      <div className="border-b border-cyan-300/10 px-4 py-4">
        <p className="text-xs font-semibold uppercase text-zinc-500">Explorer</p>
        <p className="mt-1 text-sm font-semibold text-white">{workspace.name}</p>
      </div>

      <div className="space-y-5 p-4">
        <section className="rounded-xl border border-cyan-300/10 bg-white/[0.035] p-3">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-zinc-500">
            Source setup
          </p>
          <div className="mt-3 rounded-lg border border-emerald-300/15 bg-emerald-300/10 p-3">
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 text-xs font-semibold text-emerald-100">
                <span className="h-2 w-2 rounded-full bg-emerald-300" />
                Connected
              </span>
              <span className="text-[0.68rem] font-semibold uppercase text-emerald-200/70">
                Demo source
              </span>
            </div>
            <p className="truncate text-xs font-semibold text-zinc-200">
              {workspace.engine} · {workspace.host}
            </p>
            <p className="mt-2 text-xs leading-5 text-zinc-500">
              {workspace.database} · {workspace.schema}
            </p>
          </div>
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold uppercase text-zinc-600">
              {workspace.kind === "document" ? "Collections" : "Tables"}
            </span>
            <span className="text-xs text-zinc-600">{workspace.resources.length}</span>
          </div>
          <div className="mt-3 space-y-1.5">
            {workspace.resources.map((resource, index) => (
              <button
                key={resource.name}
                className={`flex h-11 w-full items-center justify-between gap-2 rounded-lg px-2.5 text-left text-sm transition ${
                  index === 0
                    ? "bg-cyan-300/15 text-cyan-100 ring-1 ring-cyan-300/25"
                    : "text-zinc-400 hover:bg-white/[0.05] hover:text-white"
                }`}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <ResourceIcon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{resource.name}</span>
                </span>
                <span className="shrink-0 rounded-full bg-white/[0.06] px-2 py-0.5 text-[0.68rem] font-semibold text-zinc-500">
                  {resource.count}
                </span>
              </button>
            ))}
            {workspace.resources.length === 0 ? (
              <p className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-xs leading-5 text-zinc-500">
                This workspace is planned and will unlock when the product engine is active.
              </p>
            ) : null}
          </div>
        </section>

        <Link
          href="/demos"
          className="inline-flex h-10 w-full items-center justify-center rounded-lg border border-white/10 text-sm font-semibold text-zinc-300 transition hover:border-cyan-300/30 hover:text-cyan-100"
        >
          Back to demos
        </Link>
      </div>
    </aside>
  );
}

function DemoHeader({ workspace }: { workspace: DemoWorkspace }) {
  const Icon = workspace.kind === "document" ? FileJson : workspace.kind === "planned" ? Sparkles : Database;

  return (
    <section className="border-b border-cyan-300/10 bg-[#080d1b]">
      <div className="grid gap-4 px-5 py-5 2xl:grid-cols-[minmax(0,1fr)_auto] 2xl:items-center">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-100">
              <Icon className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <h1 className="truncate text-2xl font-semibold text-white">{workspace.name}</h1>
              <p className="mt-1 truncate text-sm text-zinc-500">
                {workspace.engine} · {workspace.database} · {workspace.schema}
              </p>
            </div>
          </div>
          <div className="mt-4">
            <div className="mb-2 flex items-center justify-between gap-3 text-xs font-semibold text-zinc-500">
              <span className="truncate">Latest run · demo-workspace · Validated</span>
              <span className="text-cyan-200">{workspace.kind === "planned" ? "0" : "100"}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/[0.08]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                style={{ width: workspace.kind === "planned" ? "12%" : "100%" }}
              />
            </div>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-4 2xl:w-[32rem]">
          <DemoMetric icon={Rows3} label="Rows" value={String(workspace.rows)} />
          <DemoMetric icon={Database} label={workspace.kind === "document" ? "Collections" : "Tables"} value={String(workspace.resources.length)} />
          <DemoMetric icon={BarChart3} label="Columns" value={String(workspace.columns)} />
          <DemoMetric icon={Download} label="Artifacts" value={String(workspace.artifacts)} />
        </div>
      </div>
    </section>
  );
}

function DemoToolbar({ isDocument, workspace }: { isDocument: boolean; workspace: DemoWorkspace }) {
  const tabs = ["Preview", "Columns", "Profile", "Lineage", "Queries", "History", "Settings"];
  const activeView = isDocument ? "JSON" : "Table";

  return (
    <header className="border-b border-cyan-300/10 bg-[#080d1b]">
      <div className="flex min-h-16 flex-col gap-3 px-5 py-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold text-white">
              {workspace.resources[0]?.name ?? workspace.name}
            </h2>
            <span className="rounded-md border border-white/10 bg-white/[0.05] px-2 py-1 text-xs font-semibold text-zinc-400">
              {workspace.resources[0]?.count ?? 0} records
            </span>
          </div>
          <p className="mt-1 text-xs text-zinc-500">{workspace.description}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button className="inline-flex h-10 items-center gap-2 rounded-lg border border-cyan-300/25 bg-cyan-300/12 px-3 text-sm font-semibold text-cyan-100">
            <Eye className="h-4 w-4" />
            View · {activeView}
          </button>
          <button className="inline-flex h-10 items-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] px-3 text-sm font-semibold text-zinc-200">
            <Download className="h-4 w-4" />
            Download
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-3 border-t border-white/5 px-5 py-3 xl:flex-row xl:items-center xl:justify-between">
        <nav className="workspace-scrollbar-dark flex gap-1 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab}
              className={`h-9 shrink-0 rounded-lg px-4 text-sm font-semibold transition ${
                tab === "Preview"
                  ? "bg-cyan-300/10 text-cyan-200 ring-1 ring-cyan-300/25"
                  : "text-zinc-500 hover:bg-white/[0.045] hover:text-zinc-200"
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
        <div className="flex flex-wrap items-center gap-2">
          <button className="inline-flex h-9 items-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] px-3 text-sm font-semibold text-zinc-300">
            <Filter className="h-4 w-4" />
            Filter
          </button>
          <button className="inline-flex h-9 items-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] px-3 text-sm font-semibold text-zinc-300">
            <Search className="h-4 w-4" />
            Search
          </button>
        </div>
      </div>
    </header>
  );
}

function TableDemo({ workspace }: { workspace: DemoWorkspace }) {
  return (
    <div className="workspace-scrollbar-dark min-h-full overflow-auto">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead className="sticky top-0 z-10 bg-[#101727] shadow-[0_1px_0_rgba(255,255,255,0.08)]">
          <tr>
            <th className="w-14 border-b border-r border-white/10 px-3 py-3 text-xs font-semibold text-zinc-500">
              #
            </th>
            {workspace.tableColumns.map((column) => (
              <th
                key={column}
                className="min-w-44 border-b border-r border-white/10 px-3 py-3 align-bottom"
              >
                <span className="block text-sm font-semibold text-zinc-100">{column}</span>
                <span className="mt-1 block text-[0.68rem] font-semibold uppercase text-zinc-400">
                  {column === "id" ? "integer" : "text"}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {workspace.tableRows.map((row, index) => {
            const rowTone = (index + 1) % 2 === 0 ? "bg-white/[0.035]" : "bg-transparent";
            return (
              <tr key={row.id} className={`${rowTone} hover:bg-cyan-300/[0.08]`}>
                <td className="border-b border-r border-white/[0.06] px-3 py-3 text-xs font-semibold text-zinc-500">
                  {index + 1}
                </td>
                {workspace.tableColumns.map((column) => (
                  <td
                    key={column}
                    className="max-w-72 truncate border-b border-r border-white/[0.06] px-3 py-3 text-zinc-300"
                  >
                    {column === "status" ? (
                      <span className={`rounded-md px-2 py-1 text-xs font-semibold ${demoStatusClass(row[column])}`}>
                        {row[column]}
                      </span>
                    ) : (
                      row[column]
                    )}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function DocumentDemo({ workspace }: { workspace: DemoWorkspace }) {
  return (
    <div className="grid gap-4 p-5 xl:grid-cols-2">
      {workspace.documents.map((document, index) => (
        <article key={index} className="rounded-xl border border-white/10 bg-white/[0.035]">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
            <p className="text-xs font-semibold uppercase text-zinc-500">Document {index + 1}</p>
            <p className="text-xs font-semibold text-zinc-500">{workspace.resources[0]?.name}</p>
          </div>
          <pre className="workspace-scrollbar-dark max-h-96 overflow-auto p-4 text-xs leading-5 text-zinc-200">
            {JSON.stringify(document, null, 2)}
          </pre>
        </article>
      ))}
    </div>
  );
}

function PlannedDemo({ workspace }: { workspace: DemoWorkspace }) {
  return (
    <div className="grid h-full place-items-center px-6 text-center">
      <div className="max-w-lg">
        <Sparkles className="mx-auto h-10 w-10 text-zinc-600" />
        <p className="mt-4 text-lg font-semibold text-white">{workspace.name}</p>
        <p className="mt-2 text-sm leading-6 text-zinc-500">{workspace.description}</p>
      </div>
    </div>
  );
}

function DemoInspector({ workspace }: { workspace: DemoWorkspace }) {
  return (
    <aside className="flex min-h-full flex-col bg-[#060a16] text-zinc-100">
      <div className="border-b border-cyan-300/10 px-4 py-4">
        <p className="text-xs font-semibold uppercase text-zinc-500">Quick actions</p>
        <div className="mt-3 space-y-2">
          <button className="inline-flex h-10 w-full items-center gap-3 rounded-lg border border-white/10 bg-white/[0.035] px-3 text-sm font-semibold text-zinc-300">
            <GitBranch className="h-4 w-4" />
            View lineage
          </button>
          <button className="inline-flex h-10 w-full items-center gap-3 rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-3 text-sm font-semibold text-cyan-100">
            <Download className="h-4 w-4" />
            Download data
          </button>
          <button className="inline-flex h-10 w-full items-center gap-3 rounded-lg border border-white/10 bg-white/[0.035] px-3 text-sm font-semibold text-zinc-300">
            <Share2 className="h-4 w-4" />
            Share dataset
          </button>
        </div>
      </div>

      <div className="workspace-scrollbar-dark min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
        <section className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-white">Run summary</h3>
            <span className="rounded-md border border-emerald-300/25 bg-emerald-300/10 px-2 py-1 text-xs font-semibold text-emerald-100">
              Completed
            </span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <DemoTinyMetric label="Rows" value={String(workspace.rows)} />
            <DemoTinyMetric label="Generated" value={`${workspace.rows}/${workspace.rows}`} />
            <DemoTinyMetric label="Resources" value={String(workspace.resources.length)} />
            <DemoTinyMetric label="Success" value={workspace.kind === "planned" ? "Planned" : "100%"} />
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
            <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500" />
          </div>
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-cyan-300" />
            <h3 className="text-sm font-semibold text-white">Status distribution</h3>
          </div>
          <div className="mt-4 space-y-3">
            {workspace.statusCounts.map((item) => (
              <div key={item.label}>
                <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                  <span className="truncate font-semibold text-zinc-300">{item.label}</span>
                  <span className="text-zinc-400">{item.count}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/10">
                  <div
                    className={`h-full rounded-full ${item.tone}`}
                    style={{ width: `${Math.max(6, Math.round((item.count / Math.max(1, workspace.rows)) * 100))}%` }}
                  />
                </div>
              </div>
            ))}
            {workspace.statusCounts.length === 0 ? (
              <p className="text-sm leading-6 text-zinc-500">Distribution appears after the engine is active.</p>
            ) : null}
          </div>
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-zinc-400" />
            <h3 className="text-sm font-semibold text-white">Generation</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-zinc-500">
            Demo runs use deterministic seeds, local artifacts, and validation-shaped metadata so the flow stays stable during review.
          </p>
        </section>
      </div>
    </aside>
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
    <div className="rounded-xl border border-white/10 bg-white/[0.045] px-3 py-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[0.68rem] font-semibold uppercase text-zinc-500">{label}</p>
        <Icon className="h-4 w-4 text-cyan-300" />
      </div>
      <p className="mt-2 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}

function DemoTinyMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-[#0b1020] p-2">
      <p className="text-[0.68rem] font-semibold uppercase text-zinc-400">{label}</p>
      <p className="mt-1 text-sm font-semibold text-zinc-100">{value}</p>
    </div>
  );
}

function demoStatusClass(status = "") {
  if (status === "posted") {
    return "border border-cyan-300/20 bg-cyan-300/10 text-cyan-100";
  }
  if (status === "pending") {
    return "border border-amber-300/20 bg-amber-300/10 text-amber-100";
  }
  if (status === "failed") {
    return "border border-red-300/20 bg-red-300/10 text-red-100";
  }
  if (status === "reversed") {
    return "border border-fuchsia-300/20 bg-fuchsia-300/10 text-fuchsia-100";
  }
  return "border border-white/10 bg-white/[0.06] text-zinc-300";
}
