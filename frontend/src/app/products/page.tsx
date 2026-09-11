import { Database, FileJson, GitBranch, ShieldCheck } from "lucide-react";

import { ProductCatalogGrid } from "@/components/product-catalog";
import { PublicShell, Section } from "@/components/layout";
import { productCatalog } from "@/data/workbench";

const principles = [
  {
    icon: Database,
    title: "Surface-specific engines",
    detail: "Table, document, graph, and masking workflows have different integrity rules. DataBoom keeps those engines separate while sharing the same run lifecycle.",
  },
  {
    icon: FileJson,
    title: "Export contracts",
    detail: "Every product defines the artifact formats, previews, manifests, and validation reports expected by downstream engineering teams.",
  },
  {
    icon: GitBranch,
    title: "Relationship integrity",
    detail: "Generation is planned around references, ordering, and stable identifiers instead of isolated fake values.",
  },
  {
    icon: ShieldCheck,
    title: "Privacy boundary",
    detail: "Synthetic generation and masking are separate product layers so sensitive source-data workflows can mature with policy controls.",
  },
];

export default function ProductsPage() {
  return (
    <PublicShell>
      <section className="border-b border-[color:var(--border)] bg-[var(--section-bg)]">
        <div className="mx-auto max-w-[1760px] px-5 py-16 sm:px-8 lg:px-12 xl:px-16">
          <div className="grid gap-8 xl:grid-cols-[0.7fr_1fr] xl:items-end">
            <div>
              <p className="text-sm font-semibold uppercase text-[color:var(--accent-emerald)]">Product catalog</p>
              <h1 className="mt-5 max-w-4xl text-4xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-6xl">
                Four data products, one controlled generation platform.
              </h1>
            </div>
            <p className="max-w-3xl text-base leading-7 text-[color:var(--text-muted)]">
              DataBoom is organized by data surface, not demo domain. Financial, healthcare,
              commerce, and SaaS datasets are profiles that run through the right product engine.
            </p>
          </div>
        </div>
      </section>

      <Section
        id="catalog"
        eyebrow="Catalog"
        title="Choose the engine by the shape of data you need."
        subtitle="Active products are available in the workspace. Planned products stay visible because they define the platform boundaries and future architecture."
      >
        <ProductCatalogGrid products={productCatalog} />
      </Section>

      <Section
        id="principles"
        eyebrow="Architecture principles"
        title="The catalog is designed for extension, not one-off demos."
        subtitle="Each product owns its schema/spec input, generation strategy, preview surface, export formats, and validation path."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {principles.map((item) => {
            const Icon = item.icon;
            return (
              <article
                key={item.title}
                className="rounded-xl border border-[color:var(--border)] bg-[var(--surface)] p-5 transition duration-300 hover:-translate-y-1 hover:bg-[var(--surface-strong)]"
              >
                <Icon className="h-5 w-5 text-[color:var(--accent-emerald)]" />
                <h2 className="mt-5 text-lg font-semibold text-[color:var(--text-primary)]">
                  {item.title}
                </h2>
                <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">
                  {item.detail}
                </p>
              </article>
            );
          })}
        </div>
      </Section>
    </PublicShell>
  );
}
