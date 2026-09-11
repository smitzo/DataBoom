import { CheckCircle2, Clock3 } from "lucide-react";

import type { ProductCatalogItem } from "@/data/workbench";

export function ProductCatalogGrid({ products }: { products: ProductCatalogItem[] }) {
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      {products.map((product) => (
        <ProductCatalogCard key={product.name} product={product} />
      ))}
    </div>
  );
}

function ProductCatalogCard({ product }: { product: ProductCatalogItem }) {
  const Icon = product.icon;
  const active = product.status === "achieved";

  return (
    <article
      className={`group relative overflow-hidden rounded-xl border bg-[var(--surface)] p-6 transition duration-300 hover:-translate-y-1 hover:bg-[var(--surface-strong)] hover:shadow-2xl hover:shadow-[color:var(--shadow-soft)] ${product.accent}`}
    >
      <div className={`absolute inset-x-0 top-0 h-36 bg-gradient-to-r opacity-90 ${product.accent}`} />
      <div className="relative z-10">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-xl border border-current/25 bg-[var(--surface-muted)] text-current shadow-[0_0_24px_rgba(34,211,238,0.12)]">
              <Icon className="h-7 w-7" />
            </span>
            <div>
              <p className="text-sm font-semibold text-current">{product.module}</p>
              <h2 className="mt-2 text-3xl font-semibold leading-tight text-[color:var(--text-primary)]">
                {product.name}
              </h2>
            </div>
          </div>
          <ProductStatus active={active} />
        </div>

        <p className="mt-6 max-w-2xl text-lg font-medium leading-7 text-[color:var(--text-primary)]">
          {product.summary}
        </p>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-[color:var(--text-muted)]">
          {product.detail}
        </p>

        <div className="mt-6 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <CatalogPanel title="Outputs" items={product.outputs} compact />
          <CatalogPanel title="Core capabilities" items={product.capabilities} />
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          {product.useCases.map((useCase) => (
            <span
              key={useCase}
              className="rounded-md border border-[color:var(--border)] bg-[var(--surface-muted)] px-3 py-2 text-xs font-semibold uppercase text-[color:var(--text-faint)]"
            >
              {useCase}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
}

function ProductStatus({ active }: { active: boolean }) {
  const Icon = active ? CheckCircle2 : Clock3;

  return (
    <span
      className={`inline-flex w-fit items-center gap-2 rounded-md border px-3 py-2 text-xs font-semibold uppercase ${
        active
          ? "border-emerald-300/35 bg-emerald-300/10 text-[color:var(--accent-emerald)]"
          : "border-sky-300/35 bg-sky-300/10 text-[color:var(--accent-sky)]"
      }`}
    >
      <Icon className="h-4 w-4" />
      {active ? "Available" : "Roadmap"}
    </span>
  );
}

function CatalogPanel({
  title,
  items,
  compact = false,
}: {
  title: string;
  items: string[];
  compact?: boolean;
}) {
  return (
    <div className="rounded-xl border border-[color:var(--border)] bg-[var(--surface-muted)] p-4">
      <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">{title}</p>
      <div className={compact ? "mt-4 flex flex-wrap gap-2" : "mt-4 space-y-3"}>
        {items.map((item) =>
          compact ? (
            <span
              key={item}
              className="rounded-md border border-[color:var(--border)] px-2 py-1 text-xs font-semibold uppercase text-[color:var(--text-secondary)]"
            >
              {item}
            </span>
          ) : (
            <div key={item} className="flex gap-3">
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-emerald-300" />
              <p className="text-sm leading-6 text-[color:var(--text-secondary)]">{item}</p>
            </div>
          ),
        )}
      </div>
    </div>
  );
}
