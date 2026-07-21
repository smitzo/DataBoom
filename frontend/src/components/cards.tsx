import { BadgeCheck } from "lucide-react";

import { formats } from "@/data/workbench";
import type {
  DemoDatasetConfig,
  FormatConfig,
  PipelineStepConfig,
  ProfileConfig,
  ValidationMetricConfig,
} from "@/data/workbench";

export function MetricTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
      <p className="text-sm text-zinc-500">{label}</p>
      <p className={`mt-2 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

export function FormatRow({ format }: { format: FormatConfig }) {
  const Icon = format.icon;

  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-white/10 bg-black/25 px-4 py-3">
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-amber-200" />
        <span className="text-sm font-medium text-white">{format.name}</span>
      </div>
      <span className="text-xs font-medium uppercase text-zinc-500">{format.state}</span>
    </div>
  );
}

export function ProfileCard({ profile }: { profile: ProfileConfig }) {
  const Icon = profile.icon;

  return (
    <button
      className={`min-h-72 rounded-lg border bg-white/[0.03] p-5 text-left transition hover:bg-white/[0.05] ${profile.tone}`}
    >
      <div className="flex items-start justify-between gap-4">
        <span className="flex h-10 w-10 items-center justify-center rounded-md bg-white/5">
          <Icon className="h-5 w-5" />
        </span>
        {profile.selected ? <BadgeCheck className="h-5 w-5 text-emerald-300" /> : null}
      </div>
      <p className="mt-6 text-lg font-semibold text-white">{profile.name}</p>
      <p className="mt-1 text-sm font-semibold uppercase text-current">{profile.role}</p>
      <p className="mt-4 text-sm leading-6 text-zinc-400">{profile.description}</p>
      <div className="mt-6 flex flex-wrap gap-2">
        {profile.tags.map((tag) => (
          <span
            key={tag}
            className="rounded-md border border-white/10 px-2 py-1 text-xs uppercase text-zinc-500"
          >
            {tag}
          </span>
        ))}
      </div>
    </button>
  );
}

export function PipelineCard({ step }: { step: PipelineStepConfig }) {
  const Icon = step.icon;

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
      <Icon className="h-5 w-5 text-indigo-300" />
      <p className="mt-5 font-semibold text-white">{step.label}</p>
      <p className="mt-2 text-sm text-zinc-500">{step.detail}</p>
    </div>
  );
}

export function ValidationMetric({ metric }: { metric: ValidationMetricConfig }) {
  const Icon = metric.icon;

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-zinc-500">{metric.label}</p>
        <Icon className={metric.success ? "h-5 w-5 text-emerald-300" : "h-5 w-5 text-zinc-500"} />
      </div>
      <p
        className={
          metric.success
            ? "mt-5 text-2xl font-semibold text-emerald-300"
            : "mt-5 text-2xl font-semibold text-white"
        }
      >
        {metric.value}
      </p>
    </div>
  );
}

export function DemoDataset({ demo }: { demo: DemoDatasetConfig }) {
  return (
    <div className={`rounded-lg border bg-white/[0.03] p-5 ${demo.tone}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-lg font-semibold text-white">{demo.name}</p>
          <p className="mt-3 text-sm leading-6 text-zinc-400">{demo.tables}</p>
        </div>
        <BadgeCheck className="h-5 w-5 text-emerald-300" />
      </div>
      <p className="mt-8 text-sm font-semibold text-zinc-100">{demo.rows}</p>
    </div>
  );
}

export function ArtifactPanel() {
  return (
    <div className="rounded-lg border border-amber-300/25 bg-amber-400/10 p-5">
      <p className="text-lg font-semibold text-white">Output formats</p>
      <p className="mt-3 text-sm leading-6 text-zinc-400">
        The engine can export the same run into multiple local artifact types for
        analysts, backend tests, and database loading.
      </p>
      <div className="mt-6 space-y-3">
        {formats.map((format) => (
          <FormatRow key={format.name} format={format} />
        ))}
      </div>
    </div>
  );
}
