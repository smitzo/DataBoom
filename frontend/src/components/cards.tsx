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
    <div className="rounded-xl border border-[color:var(--border)] bg-[var(--surface)] p-4 transition duration-300 hover:-translate-y-0.5 hover:bg-[var(--surface-strong)]">
      <p className="text-sm font-medium text-[color:var(--text-muted)]">{label}</p>
      <p className={`mt-2 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

export function FormatRow({
  format,
  variant = "theme",
}: {
  format: FormatConfig;
  variant?: "theme" | "dark";
}) {
  const Icon = format.icon;
  const className =
    variant === "dark"
      ? "flex items-center justify-between gap-4 rounded-md border border-white/10 bg-black/25 px-4 py-3"
      : "flex items-center justify-between gap-4 rounded-md border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 py-3";
  const textClassName =
    variant === "dark" ? "text-sm font-medium text-white" : "text-sm font-medium text-[color:var(--text-primary)]";
  const stateClassName =
    variant === "dark"
      ? "text-xs font-medium uppercase text-zinc-500"
      : "text-xs font-medium uppercase text-[color:var(--text-faint)]";

  return (
    <div className={className}>
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-[color:var(--accent-amber)]" />
        <span className={textClassName}>{format.name}</span>
      </div>
      <span className={stateClassName}>{format.state}</span>
    </div>
  );
}

export function ProfileCard({ profile }: { profile: ProfileConfig }) {
  const Icon = profile.icon;

  return (
    <article
      className={`min-h-72 rounded-xl border bg-[var(--surface)] p-6 text-left transition duration-300 hover:-translate-y-1 hover:bg-[var(--surface-strong)] hover:shadow-2xl hover:shadow-[color:var(--shadow-soft)] ${profile.tone}`}
    >
      <div className="flex items-start justify-between gap-4">
        <span className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--surface-strong)]">
          <Icon className="h-5 w-5" />
        </span>
        {profile.selected ? <BadgeCheck className="h-5 w-5 text-[color:var(--accent-emerald)]" /> : null}
      </div>
      <p className="mt-6 text-xl font-semibold text-[color:var(--text-primary)]">{profile.name}</p>
      <p className="mt-1 text-sm font-medium text-current">{profile.role}</p>
      <p className="mt-4 text-sm leading-6 text-[color:var(--text-muted)]">{profile.description}</p>
      <div className="mt-6 flex flex-wrap gap-2">
        {profile.tags.map((tag) => (
          <span
            key={tag}
            className="rounded-md border border-[color:var(--border)] px-2 py-1 text-xs uppercase text-[color:var(--text-faint)]"
          >
            {tag}
          </span>
        ))}
      </div>
    </article>
  );
}

export function PipelineCard({ step }: { step: PipelineStepConfig }) {
  const Icon = step.icon;

  return (
    <div className="rounded-xl border border-[color:var(--border)] bg-[var(--surface)] p-5 transition duration-300 hover:-translate-y-1 hover:bg-[var(--surface-strong)]">
      <Icon className="h-5 w-5 text-indigo-500" />
      <p className="mt-5 font-semibold text-[color:var(--text-primary)]">{step.label}</p>
      <p className="mt-2 text-sm text-[color:var(--text-muted)]">{step.detail}</p>
    </div>
  );
}

export function ValidationMetric({ metric }: { metric: ValidationMetricConfig }) {
  const Icon = metric.icon;

  return (
    <div className="rounded-xl border border-[color:var(--border)] bg-[var(--surface)] p-5 transition duration-300 hover:-translate-y-1 hover:bg-[var(--surface-strong)]">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-[color:var(--text-muted)]">{metric.label}</p>
        <Icon className={metric.success ? "h-5 w-5 text-[color:var(--accent-emerald)]" : "h-5 w-5 text-[color:var(--text-faint)]"} />
      </div>
      <p
        className={
          metric.success
            ? "mt-5 text-2xl font-semibold text-[color:var(--accent-emerald)]"
            : "mt-5 text-2xl font-semibold text-[color:var(--text-primary)]"
        }
      >
        {metric.value}
      </p>
    </div>
  );
}

export function DemoDataset({ demo }: { demo: DemoDatasetConfig }) {
  return (
    <div className={`rounded-xl border bg-[var(--surface)] p-5 transition duration-300 hover:-translate-y-1 hover:bg-[var(--surface-strong)] ${demo.tone}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-lg font-semibold text-[color:var(--text-primary)]">{demo.name}</p>
          <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{demo.tables}</p>
        </div>
        <BadgeCheck className="h-5 w-5 text-[color:var(--accent-emerald)]" />
      </div>
      <p className="mt-8 text-sm font-semibold text-[color:var(--text-secondary)]">{demo.rows}</p>
    </div>
  );
}

export function ArtifactPanel() {
  return (
    <div className="rounded-xl border border-amber-300/35 bg-amber-400/10 p-5">
      <p className="text-lg font-semibold text-[color:var(--text-primary)]">Output formats</p>
      <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
        The engine can export the same run into multiple local artifact types for
        analysis, application tests, and database loading.
      </p>
      <div className="mt-6 space-y-3">
        {formats.map((format) => (
          <FormatRow key={format.name} format={format} />
        ))}
      </div>
    </div>
  );
}
