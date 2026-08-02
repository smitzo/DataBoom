import { ArtifactPanel, DemoDataset, PipelineCard, ProfileCard, ValidationMetric } from "@/components/cards";
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
        title="Whacky names, serious data contracts."
        subtitle="Generator-Boom modules add realistic values where the domain benefits from them. Masker-Boom stays visible as the future privacy layer."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {profiles.map((profile) => (
            <ProfileCard key={profile.name} profile={profile} />
          ))}
        </div>
      </Section>

      <Section
        id="pipeline"
        eyebrow="Engine pipeline"
        title="Built around relationships, exports, and validation."
        subtitle="The UI mirrors the backend architecture so every future API endpoint has a natural place to land."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {pipeline.map((step) => (
            <PipelineCard key={step.label} step={step} />
          ))}
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
