import {
  ArtifactPanel,
  DemoDataset,
  PipelineCard,
  ProfileCard,
  ValidationMetric,
} from "@/components/cards";
import { Hero } from "@/components/hero";
import { Announcement, Header, Section } from "@/components/layout";
import { Roadmap } from "@/components/roadmap";
import { demos, pipeline, profiles, validationMetrics } from "@/data/workbench";

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <Announcement />
      <Header />
      <Hero />

      <Section
        id="profiles"
        eyebrow="Product modules"
        title="Start public, then enter your dashboard."
        subtitle="The public page explains the product family. The dashboard is where you subscribe to modules, generate data, preview tables, and download outputs."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {profiles.map((profile) => (
            <ProfileCard key={profile.name} profile={profile} />
          ))}
        </div>
      </Section>

      <Section
        id="pipeline"
        eyebrow="Full-stack flow"
        title="Plan, generate, validate, preview, download."
        subtitle="Inspired by mature synthetic-data product flows: marketing explains the value, login opens the workspace, and each product drives a repeatable backend run."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {pipeline.map((step) => (
            <PipelineCard key={step.label} step={step} />
          ))}
        </div>
      </Section>

      <Section
        id="dashboard"
        eyebrow="My dashboard"
        title="Already logged in? Jump straight into your workspace."
        subtitle="Your dashboard keeps subscribed products, recent runs, generated table previews, and artifact downloads together."
      >
        <div className="rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-6">
          <p className="text-xl font-semibold text-white">DataBoom product console</p>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-400">
            Use demo credentials on the login page, subscribe to Bank-O-Boom, Health-Boom,
            Boom-Commerce, or Schema-Boom, then generate data through the FastAPI backend.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <a
              href="/dashboard"
              className="inline-flex h-11 items-center rounded-md bg-white px-5 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-100"
            >
              Open My Dashboard
            </a>
            <a
              href="/login"
              className="inline-flex h-11 items-center rounded-md border border-white/15 px-5 text-sm font-semibold text-white transition hover:border-white/35"
            >
              Login with demo
            </a>
          </div>
        </div>
      </Section>

      <Roadmap />

      <Section
        id="validation"
        eyebrow="Validation snapshot"
        title="Current baseline is visible by default."
        subtitle="Phase 1 generated and validated a 100k-record benchmark with local artifacts."
      >
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {validationMetrics.map((metric) => (
            <ValidationMetric key={metric.label} metric={metric} />
          ))}
        </div>
      </Section>

      <Section
        id="demos"
        eyebrow="Demo data"
        title="Checked-in datasets for product demos and regression checks."
        subtitle="Bank-O-Boom and Health-Boom CSVs are already generated through Generator-Boom."
      >
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr_0.9fr]">
          {demos.map((demo) => (
            <DemoDataset key={demo.name} demo={demo} />
          ))}
          <ArtifactPanel />
        </div>
      </Section>
    </main>
  );
}
