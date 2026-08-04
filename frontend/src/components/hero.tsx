import { MetricTile } from "@/components/cards";
import { ControlCenter } from "@/components/control-center";
import { HeroActions } from "@/components/public-session-actions";
import { heroMetrics } from "@/data/workbench";

export function Hero() {
  return (
    <section id="platform" className="relative overflow-hidden border-b border-white/10">
      <div className="absolute inset-y-0 right-0 hidden w-1/2 bg-gradient-to-l from-zinc-800/35 to-transparent lg:block" />
      <div className="mx-auto grid min-h-[760px] max-w-[1680px] gap-10 px-5 py-12 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-12 xl:px-16">
        <div className="relative z-10 max-w-3xl">
          <div className="flex flex-wrap items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-white shadow-[0_0_16px_rgba(255,255,255,0.85)]" />
            <span className="text-sm font-medium uppercase text-zinc-400">
              Open-source data generation and masking platform
            </span>
            <span className="rounded-md border border-emerald-300/40 bg-emerald-300/10 px-3 py-1 text-xs font-semibold uppercase text-emerald-200">
              Phase 1 ready
            </span>
          </div>

          <h1 className="mt-9 text-5xl font-semibold leading-none text-white sm:text-6xl lg:text-7xl">
            One workspace to generate{" "}
            <span className="font-serif italic text-zinc-300">domain-aware</span>{" "}
            structured data.
          </h1>

          <div className="mt-8 max-w-2xl border-l border-white/20 pl-5">
            <p className="text-xl font-semibold leading-8 text-white">
              Table-Boom turns schemas into validated table artifacts, Docu-Boom
              creates nested NoSQL documents, and Masker-Boom is planned for redaction.
            </p>
          </div>

          <p className="mt-6 max-w-2xl text-base leading-7 text-zinc-400">
            The backend already handles schema parsing, dependency ordering,
            deterministic generation, local exports, and validation reports. Use it
            to create high-volume demo, test, and analytics datasets without asking
            an LLM to stream every row.
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <HeroActions />
          </div>

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
