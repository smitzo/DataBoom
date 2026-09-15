"use client";

import {
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Loader2,
  Play,
  Send,
  Sparkles,
  X,
} from "lucide-react";

import type { GenerationRun, PlanProposal, Product } from "@/lib/api";

export type WorkspaceAgentStatus =
  | "idle"
  | "subscribing"
  | "planning"
  | "generating"
  | "complete"
  | "error";

export type WorkspaceAgentStep = {
  label: string;
  detail: string;
  state: "done" | "active" | "waiting";
};

export type WorkspaceInsight = {
  title: string;
  values: { label: string; count: number; percent: number }[];
};

type WorkspaceRunPanelProps = {
  currentPlan: PlanProposal | null;
  insight: WorkspaceInsight | null;
  onApproveAndGenerate: () => void;
  onClose: () => void;
  onCreatePlan: () => void;
  onPromptChange: (value: string) => void;
  onRejectPlan: () => void;
  onSubscribe: () => void;
  prompt: string;
  run: GenerationRun | null;
  selectedProduct: Product | null;
  status: WorkspaceAgentStatus;
  steps: WorkspaceAgentStep[];
  subscribed: boolean;
  visibleRows: number;
};

export function WorkspaceRunPanel({
  currentPlan,
  insight,
  onApproveAndGenerate,
  onClose,
  onCreatePlan,
  onPromptChange,
  onRejectPlan,
  onSubscribe,
  prompt,
  run,
  selectedProduct,
  status,
  steps,
  subscribed,
  visibleRows,
}: WorkspaceRunPanelProps) {
  const busy =
    status === "planning" ||
    status === "generating" ||
    status === "subscribing" ||
    run?.status === "running";
  const state = runState(run);

  return (
    <aside className="flex min-h-full flex-col border-l border-cyan-300/10 bg-[#060a16] text-zinc-100">
      <div className="flex h-16 items-center justify-between gap-3 border-b border-white/10 px-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-500">Run</p>
          <p className="truncate text-sm font-semibold text-white">
            {selectedProduct?.name ?? "Workspace"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${state.className}`}>
            {run?.status === "running" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : run?.validation?.passed ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <CircleAlert className="h-3.5 w-3.5" />
            )}
            {state.label}
          </span>
          <button
            aria-label="Close run panel"
            className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 text-zinc-500 transition hover:border-cyan-300/30 hover:text-white"
            onClick={onClose}
            title="Close run panel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="workspace-scrollbar-dark min-h-0 flex-1 overflow-y-auto">
        <section className="border-b border-white/10 p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <label className="text-xs font-semibold uppercase text-zinc-500" htmlFor="generation-brief">
              Generation brief
            </label>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-200">
              <Sparkles className="h-3.5 w-3.5" />
              Seeded
            </span>
          </div>
          <textarea
            className="h-24 w-full resize-none rounded-lg border border-white/10 bg-[#0b1020] p-3 text-sm leading-6 text-zinc-100 outline-none transition placeholder:text-zinc-700 focus:border-cyan-300/45"
            disabled={busy}
            id="generation-brief"
            onChange={(event) => onPromptChange(event.target.value)}
            value={prompt}
          />

          {currentPlan ? (
            <PlanReview
              busy={busy}
              onApproveAndGenerate={onApproveAndGenerate}
              onReject={onRejectPlan}
              plan={currentPlan}
              status={status}
            />
          ) : (
            <div className="mt-3 flex items-center justify-between gap-3">
              <span className="text-xs text-zinc-500">{visibleRows} preview rows</span>
              {subscribed ? (
                <button
                  className="inline-flex h-9 items-center gap-2 rounded-lg bg-cyan-300 px-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={busy || !prompt.trim() || selectedProduct?.status !== "active"}
                  onClick={onCreatePlan}
                >
                  {status === "planning" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  {status === "planning" ? "Planning" : "Review plan"}
                </button>
              ) : (
                <button
                  className="inline-flex h-9 items-center gap-2 rounded-lg bg-cyan-300 px-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={busy || selectedProduct?.status !== "active"}
                  onClick={onSubscribe}
                >
                  {status === "subscribing" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  Enable
                </button>
              )}
            </div>
          )}
        </section>

        {run ? <RunSummary run={run} visibleRows={visibleRows} /> : null}

        <details className="group border-b border-white/10 p-4">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-zinc-200">
            Execution
            <ChevronDown className="h-4 w-4 text-zinc-500 transition group-open:rotate-180" />
          </summary>
          <div className="mt-4 space-y-3">
            {steps.map((step) => (
              <div className="flex items-start gap-3" key={step.label}>
                <span
                  className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                    step.state === "active"
                      ? "animate-pulse bg-cyan-300"
                      : step.state === "done"
                        ? "bg-emerald-300"
                        : "bg-zinc-700"
                  }`}
                />
                <div>
                  <p className="text-sm font-semibold text-zinc-200">{step.label}</p>
                  <p className="mt-1 text-xs leading-5 text-zinc-500">{step.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </details>

        {insight ? <InsightPanel insight={insight} /> : null}
      </div>
    </aside>
  );
}

function PlanReview({
  busy,
  onApproveAndGenerate,
  onReject,
  plan,
  status,
}: {
  busy: boolean;
  onApproveAndGenerate: () => void;
  onReject: () => void;
  plan: PlanProposal;
  status: WorkspaceAgentStatus;
}) {
  const totalRecords = plan.decision.resources.reduce(
    (total, resource) => total + resource.target_count,
    0,
  );
  const isDraft = plan.review_status === "draft";
  const isRejected = plan.review_status === "rejected";
  const plannerLabel = plan.telemetry.mode === "openai" ? "LLM" : "Deterministic";

  return (
    <div className="mt-3 border-t border-white/10 pt-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm leading-5 text-zinc-300">{plan.decision.summary}</p>
        <span className="shrink-0 text-xs font-semibold uppercase text-cyan-200">
          {plan.review_status}
        </span>
      </div>
      <p className="mt-2 text-xs text-zinc-500">
        {formatNumber(totalRecords)} rows · {plannerLabel}
      </p>

      <div className="mt-3 max-h-28 space-y-1.5 overflow-y-auto pr-1 text-xs">
        {plan.decision.resources.map((resource) => (
          <div className="flex items-center justify-between gap-3" key={resource.name}>
            <span className="truncate text-zinc-500">{resource.name}</span>
            <span className="shrink-0 font-semibold text-zinc-300">
              {formatNumber(resource.target_count)}
            </span>
          </div>
        ))}
      </div>

      {plan.decision.warnings[0] ? (
        <p className="mt-3 text-xs leading-5 text-amber-200">{plan.decision.warnings[0]}</p>
      ) : null}

      {isRejected ? (
        <p className="mt-3 text-xs text-zinc-500">Revise the brief to create another plan.</p>
      ) : (
        <div className="mt-3 flex items-center justify-end gap-2">
          {isDraft ? (
            <button
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-white/10 px-3 text-xs font-semibold text-zinc-300 transition hover:border-rose-300/30 hover:text-rose-200 disabled:opacity-50"
              disabled={busy}
              onClick={onReject}
            >
              <X className="h-3.5 w-3.5" />
              Reject
            </button>
          ) : null}
          <button
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-cyan-300 px-3 text-xs font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:opacity-50"
            disabled={busy}
            onClick={onApproveAndGenerate}
          >
            {status === "planning" || status === "generating" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
            {status === "planning"
              ? "Approving"
              : status === "generating"
                ? "Generating"
                : isDraft
                  ? "Approve and generate"
                  : "Generate"}
          </button>
        </div>
      )}
    </div>
  );
}

function RunSummary({ run, visibleRows }: { run: GenerationRun; visibleRows: number }) {
  const progress = progressPercent(run);

  return (
    <section className="border-b border-white/10 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-white">Latest run</h3>
        <span className="text-xs font-semibold uppercase text-zinc-500">{run.status}</span>
      </div>
      <div className="mt-4 grid grid-cols-3 divide-x divide-white/10">
        <RunMetric label="Rows" value={formatNumber(run.generated_rows)} />
        <RunMetric label="Preview" value={String(visibleRows)} />
        <RunMetric
          label={run.status === "running" ? "ETA" : "Duration"}
          value={formatDuration(
            run.status === "running" ? run.remaining_seconds ?? run.expected_seconds : totalRunSeconds(run),
          )}
        />
      </div>
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-zinc-500">
        <span>{formatRate(run.rows_per_second)}</span>
        <span>{progress}%</span>
      </div>

      {run.operation_timings.length ? (
        <details className="group mt-4 border-t border-white/10 pt-3">
          <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-semibold text-zinc-400">
            Timings
            <ChevronDown className="h-3.5 w-3.5 transition group-open:rotate-180" />
          </summary>
          <div className="mt-3 space-y-2">
            {run.operation_timings.map((timing) => (
              <div className="flex items-center justify-between gap-3 text-xs" key={timing.operation}>
                <span className="truncate text-zinc-500">{formatOperationName(timing.operation)}</span>
                <span className="shrink-0 font-semibold text-zinc-300">
                  {formatDuration(timing.elapsed_seconds)}
                </span>
              </div>
            ))}
          </div>
        </details>
      ) : null}
    </section>
  );
}

function RunMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-3 first:pl-0 last:pr-0">
      <p className="text-[0.68rem] font-semibold uppercase text-zinc-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-zinc-100">{value}</p>
    </div>
  );
}

function InsightPanel({ insight }: { insight: WorkspaceInsight }) {
  return (
    <details className="group p-4">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-zinc-200">
        {insight.title}
        <ChevronDown className="h-4 w-4 text-zinc-500 transition group-open:rotate-180" />
      </summary>
      <div className="mt-4 space-y-3">
        {insight.values.map((item) => (
          <div key={item.label}>
            <div className="mb-1 flex items-center justify-between gap-3 text-xs">
              <span className="truncate text-zinc-400">{item.label}</span>
              <span className="text-zinc-500">{item.count}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-cyan-500" style={{ width: `${item.percent}%` }} />
            </div>
          </div>
        ))}
      </div>
    </details>
  );
}

function runState(run: GenerationRun | null) {
  if (run?.status === "running") {
    return { label: "Running", className: "text-cyan-200" };
  }
  if (run?.validation?.passed) {
    return { label: "Validated", className: "text-emerald-200" };
  }
  return { label: "Ready", className: "text-zinc-500" };
}

function progressPercent(run: GenerationRun) {
  if (run.total_rows <= 0) {
    return run.status === "completed" ? 100 : 0;
  }
  return Math.min(100, Math.round((run.generated_rows / run.total_rows) * 100));
}

function totalRunSeconds(run: GenerationRun) {
  return run.operation_timings.reduce((total, timing) => total + timing.elapsed_seconds, 0);
}

function formatDuration(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined) {
    return "--";
  }
  if (seconds < 1) {
    return `${Math.round(seconds * 1_000)}ms`;
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

function formatRate(rate: number | null) {
  return rate ? `${formatNumber(Math.round(rate))}/s` : "--";
}

function formatOperationName(operation: string) {
  return operation
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}
