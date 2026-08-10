import { ArrowRight } from "lucide-react";

import { MetricTile } from "@/components/cards";
import { ControlCenter } from "@/components/control-center";
import { heroMetrics } from "@/data/workbench";

export function Hero() {
  return (
    <section id="platform" className="relative overflow-hidden border-b border-[color:var(--border)]">
      <div className="absolute inset-y-0 right-0 hidden w-1/2 bg-gradient-to-l from-emerald-500/10 to-transparent lg:block" />
      <div className="absolute left-0 right-0 top-28 hidden h-px bg-gradient-to-r from-transparent via-cyan-300/40 to-transparent lg:block" />
      <div className="absolute bottom-10 left-0 right-0 hidden h-px bg-gradient-to-r from-emerald-300/0 via-emerald-300/30 to-sky-300/0 opacity-60 motion-safe:animate-pulse lg:block" />
      <div className="mx-auto grid min-h-[760px] max-w-[1680px] gap-10 px-5 py-12 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-12 xl:px-16">
        <div className="relative z-10 max-w-3xl">
          <div className="flex flex-wrap items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_16px_rgba(110,231,183,0.85)]" />
            <span className="text-sm font-medium uppercase text-[color:var(--text-muted)]">
              Controlled synthetic data platform
            </span>
            <span className="rounded-md border border-emerald-300/40 bg-emerald-300/10 px-3 py-1 text-xs font-semibold uppercase text-emerald-200">
              Relational and document engines active
            </span>
          </div>

          <h1 className="mt-9 text-5xl font-semibold leading-none text-[color:var(--text-primary)] sm:text-6xl lg:text-7xl">
            Synthetic data infrastructure for{" "}
            <span className="font-serif italic text-[color:var(--text-secondary)]">high-trust</span>{" "}
            product teams.
          </h1>

          <div className="mt-8 max-w-2xl border-l border-[color:var(--border)] pl-5">
            <p className="text-xl font-semibold leading-8 text-[color:var(--text-primary)]">
              Generate realistic table and document datasets with repeatable seeds,
              referential integrity, validation reports, and export-ready artifacts.
            </p>
          </div>

          <p className="mt-6 max-w-2xl text-base leading-7 text-[color:var(--text-muted)]">
            DataBoom is designed as an engine layer, not a prompt that prints rows.
            Table-Boom, Docu-Boom, Graph-Boom, and Masker-Boom separate data surfaces
            so generation, masking, validation, and deployment can scale cleanly.
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

        <ControlCenter showApiPanel={false} />
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
