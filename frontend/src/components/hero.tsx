import { ArrowRight } from "lucide-react";

import { MetricTile } from "@/components/cards";
import { ControlCenter } from "@/components/control-center";
import { heroMetrics } from "@/data/workbench";

export function Hero() {
  return (
    <section id="platform" className="relative overflow-hidden border-b border-[color:var(--border)]">
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(5,7,20,0.9),rgba(5,7,20,0.68)_48%,rgba(8,19,31,0.74))]" />
      <div className="absolute inset-y-0 right-0 hidden w-[56%] bg-[radial-gradient(circle_at_54%_36%,rgba(14,165,233,0.18),transparent_34%),radial-gradient(circle_at_82%_58%,rgba(45,212,191,0.08),transparent_32%)] lg:block" />
      <div className="absolute left-0 right-0 top-28 hidden h-px bg-gradient-to-r from-transparent via-cyan-300/35 to-transparent lg:block" />
      <div className="absolute bottom-10 left-0 right-0 hidden h-px bg-gradient-to-r from-emerald-300/0 via-cyan-300/25 to-sky-300/0 opacity-60 motion-safe:animate-pulse lg:block" />
      <div className="relative mx-auto grid min-h-[780px] max-w-[1760px] gap-12 px-5 py-14 sm:px-8 lg:grid-cols-[0.92fr_1.08fr] lg:items-start lg:px-12 lg:py-20 xl:px-16">
        <div className="relative z-10 max-w-3xl lg:pt-6">
          <div className="flex flex-wrap items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_16px_rgba(110,231,183,0.85)]" />
            <span className="text-sm font-semibold uppercase text-[color:var(--text-muted)]">
              Synthetic data operating layer
            </span>
            <span className="rounded-md border border-emerald-300/40 bg-emerald-300/10 px-3 py-1 text-xs font-semibold uppercase text-emerald-200">
              Table and document engines live
            </span>
          </div>

          <h1 className="mt-9 text-5xl font-semibold leading-[1.03] text-[color:var(--text-primary)] sm:text-6xl lg:text-[4.75rem]">
            Generate production-shaped data without copying production.
          </h1>

          <div className="mt-8 max-w-2xl border-l border-[color:var(--border)] pl-5">
            <p className="text-xl font-medium leading-8 text-[color:var(--text-secondary)]">
              DataBoom turns schemas and product requirements into repeatable table and
              document datasets with referential integrity, validation reports, and
              export-ready artifacts.
            </p>
          </div>

          <p className="mt-6 max-w-2xl text-base leading-7 text-[color:var(--text-muted)]">
            The platform separates the generation engine from product surfaces:
            Table-Boom for relational data, Docu-Boom for document data, Graph-Boom for
            connected data, and Masker-Boom for privacy-preserving transformations.
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
              href="/roadmap"
              className="inline-flex h-12 items-center gap-2 rounded-md border border-[color:var(--border)] px-6 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[var(--surface)]"
            >
              Review roadmap
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
