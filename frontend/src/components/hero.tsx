import { ArrowRight } from "lucide-react";

import { MetricTile } from "@/components/cards";
import { ControlCenter } from "@/components/control-center";
import { heroMetrics } from "@/data/workbench";

export function Hero() {
  return (
    <section
      id="platform"
      className="hero-shell relative overflow-hidden border-b border-[color:var(--hero-border)]"
    >
      <div className="hero-overlay absolute inset-0" />
      <div className="hero-right-glow absolute inset-y-0 right-0 hidden w-[56%] lg:block" />
      <div className="absolute left-0 right-0 top-28 hidden h-px bg-gradient-to-r from-transparent via-cyan-300/35 to-transparent lg:block" />
      <div className="absolute bottom-10 left-0 right-0 hidden h-px bg-gradient-to-r from-emerald-300/0 via-cyan-300/25 to-sky-300/0 opacity-60 motion-safe:animate-pulse lg:block" />
      <div className="relative mx-auto grid min-h-[780px] max-w-[1760px] gap-12 px-5 py-14 sm:px-8 lg:grid-cols-[0.92fr_1.08fr] lg:items-start lg:px-12 lg:py-20 xl:px-16">
        <div className="relative z-10 max-w-3xl lg:pt-6">
          <div className="flex flex-wrap items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_16px_rgba(110,231,183,0.85)]" />
            <span className="text-sm font-semibold uppercase text-[color:var(--hero-text-muted)]">
              Synthetic data operating layer
            </span>
            <span className="rounded-md border border-emerald-400/40 bg-emerald-400/10 px-3 py-1 text-xs font-semibold uppercase text-[color:var(--accent-emerald)]">
              Table and document engines live
            </span>
          </div>

          <h1 className="mt-9 text-5xl font-medium leading-[1.03] text-[color:var(--hero-text-primary)] sm:text-6xl lg:text-[4.85rem]">
            One synthetic data platform for every{" "}
            <span className="font-serif italic text-[color:var(--hero-text-secondary)]">
              non-production
            </span>{" "}
            dataset.
          </h1>

          <div className="mt-8 max-w-2xl border-l border-[color:var(--hero-border)] pl-5">
            <p className="text-xl font-medium leading-8 text-[color:var(--hero-text-secondary)]">
              Generate finance, healthcare, commerce, and SaaS-style data from schemas
              without handing production rows to prompts, scripts, or stale seed dumps.
            </p>
          </div>

          <p className="mt-6 max-w-2xl text-base leading-7 text-[color:var(--hero-text-muted)]">
            DataBoom gives engineering teams a controlled engine for table, document,
            graph, and masked data with deterministic runs, validation reports, and
            export-ready artifacts.
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <a
              href="/products"
              className="inline-flex h-12 items-center gap-2 rounded-md bg-emerald-300 px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
            >
              Explore products
              <ArrowRight className="h-4 w-4" />
            </a>
            <a
              href="/#what-is-databoom"
              className="inline-flex h-12 items-center gap-2 rounded-md border border-[color:var(--hero-border)] bg-[var(--hero-surface)] px-6 text-sm font-semibold text-[color:var(--hero-text-primary)] transition hover:bg-[var(--surface-strong)]"
            >
              See the platform
            </a>
          </div>

          <DataPulseRail />

          <div className="mt-12 grid gap-3 sm:grid-cols-3">
            {heroMetrics.map((metric) => (
              <MetricTile key={metric.label} {...metric} />
            ))}
          </div>
        </div>

        <div className="relative z-10 lg:pt-14 xl:pt-20">
          <ControlCenter showApiPanel={false} />
        </div>
      </div>
    </section>
  );
}

function DataPulseRail() {
  const bars = [
    "h-4 bg-emerald-300/50",
    "h-7 bg-cyan-300/70",
    "h-10 bg-sky-300/60",
    "h-5 bg-emerald-300/60",
    "h-12 bg-cyan-300/80",
    "h-8 bg-sky-300/55",
    "h-6 bg-emerald-300/50",
    "h-11 bg-cyan-300/70",
    "h-5 bg-sky-300/60",
    "h-9 bg-emerald-300/55",
  ];

  return (
    <div className="mt-10 flex h-14 items-end gap-2" aria-hidden="true">
      {bars.map((bar, index) => (
        <span
          key={`${bar}-${index}`}
          className={`w-1.5 rounded-full motion-safe:animate-pulse ${bar}`}
          style={{ animationDelay: `${index * 90}ms` }}
        />
      ))}
      <span className="ml-3 h-px flex-1 bg-gradient-to-r from-cyan-300/50 to-transparent" />
    </div>
  );
}
