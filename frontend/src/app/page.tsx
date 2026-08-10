import { ArrowRight, Database, FileJson, ShieldCheck } from "lucide-react";

import {
  PipelineCard,
  ProfileCard,
  ValidationMetric,
} from "@/components/cards";
import { Hero } from "@/components/hero";
import { PublicShell, Section } from "@/components/layout";
import { pipeline, profiles, validationMetrics } from "@/data/workbench";

export default function Home() {
  return (
    <PublicShell>
      <Hero />

      <Section
        id="platform"
        eyebrow="Core platform"
        title="Synthetic data generation needs an engine, not a giant text response."
        subtitle="DataBoom reads structure, plans dependencies, generates records deterministically, exports artifacts, and validates the result. LLMs can assist planning later; the engine owns high-volume execution."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {pipeline.map((step) => (
            <PipelineCard key={step.label} step={step} />
          ))}
        </div>
      </Section>

      <Section
        id="products"
        eyebrow="Products"
        title="Four product surfaces, one shared generation workflow."
        subtitle="Table-Boom and Docu-Boom are active. Graph-Boom and Masker-Boom define the next platform surfaces without mixing product architecture with use-case domains."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {profiles.map((profile) => (
            <ProfileCard key={profile.name} profile={profile} />
          ))}
        </div>
        <a
          href="/products"
          className="mt-6 inline-flex h-11 items-center gap-2 rounded-md bg-emerald-300 px-5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
        >
          View products
          <ArrowRight className="h-4 w-4" />
        </a>
      </Section>

      <Section
        id="proof"
        eyebrow="Current proof"
        title="The generation workflow is measurable end to end."
        subtitle="The stack can authenticate, subscribe to active products, run the FastAPI backend, preview generated records, and download local artifacts."
      >
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {validationMetrics.map((metric) => (
            <ValidationMetric key={metric.label} metric={metric} />
          ))}
        </div>
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <ProofCard
            icon={Database}
            title="Relational"
            detail="Table-Boom preserves primary keys, foreign keys, row counts, and local CSV/JSON/SQL exports."
          />
          <ProofCard
            icon={FileJson}
            title="Documents"
            detail="Docu-Boom writes nested JSON and NDJSON collections with top-document previews."
          />
          <ProofCard
            icon={ShieldCheck}
            title="Validation"
            detail="Runs produce manifests and validation reports before the frontend exposes artifacts."
          />
        </div>
      </Section>
    </PublicShell>
  );
}

function ProofCard({
  icon: Icon,
  title,
  detail,
}: {
  icon: typeof Database;
  title: string;
  detail: string;
}) {
  return (
    <article className="rounded-lg border border-[color:var(--border)] bg-[var(--surface)] p-5">
      <Icon className="h-5 w-5 text-emerald-300" />
      <h3 className="mt-5 text-lg font-semibold text-[color:var(--text-primary)]">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{detail}</p>
    </article>
  );
}
