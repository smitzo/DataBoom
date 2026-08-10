import {
  Activity,
  Database,
  Download,
  GitBranch,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import type { ComponentType } from "react";

import { ApiRunPanel } from "@/components/api-run-panel";
import { FormatRow } from "@/components/cards";
import { formats } from "@/data/workbench";

export function ControlCenter({ showApiPanel = true }: { showApiPanel?: boolean }) {
  return (
    <div className="relative z-10 lg:pl-4">
      <div className="overflow-hidden rounded-xl border border-white/15 bg-[#090b13]/95 shadow-[0_28px_90px_rgba(0,0,0,0.5)]">
        <div className="flex h-14 items-center justify-between border-b border-white/10 px-5">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-zinc-700" />
            <span className="h-3 w-3 rounded-full bg-zinc-700" />
            <span className="h-3 w-3 rounded-full bg-zinc-700" />
          </div>
          <span className="rounded-full border border-cyan-300/25 bg-cyan-300/10 px-4 py-1.5 text-xs font-semibold text-cyan-100">
            Run Control Center
          </span>
        </div>

        <div className="grid min-h-[520px] lg:grid-cols-[220px_1fr]">
          <aside className="hidden border-r border-white/10 p-5 lg:block">
            <p className="text-xs font-semibold uppercase text-zinc-500">Navigation</p>
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
                <span className="text-sm font-medium text-zinc-200">Local disk</span>
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
              </div>
            </div>
          </aside>

          <div className="p-5 sm:p-6">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <p className="text-2xl font-semibold text-white">Synthetic data run</p>
                <p className="mt-2 text-sm text-zinc-400">PostgreSQL schema to local artifacts</p>
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
              <div className="rounded-lg border border-cyan-400/30 bg-cyan-500/10 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold text-white">Relationship plan</p>
                    <p className="mt-1 text-sm text-zinc-400">Parent rows feed child keys.</p>
                  </div>
                  <GitBranch className="h-5 w-5 text-cyan-300" />
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
                    <FormatRow key={format.name} format={format} variant="dark" />
                  ))}
                </div>
              </div>
            </div>

            {showApiPanel ? <ApiRunPanel /> : null}
          </div>
        </div>
      </div>
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
        active ? "bg-cyan-300/10 text-white" : "text-zinc-500"
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
      : "border-cyan-300/25 bg-cyan-300/10 text-cyan-200";

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
        <span className="text-xs font-semibold text-cyan-300">{step}</span>
        <span className="truncate text-sm font-medium text-white">{label}</span>
      </div>
      <span className="text-right text-xs text-zinc-500">{detail}</span>
    </div>
  );
}
