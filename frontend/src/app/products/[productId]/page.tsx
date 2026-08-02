"use client";

import { ArrowLeft, CheckCircle2, Loader2, Rocket } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { GenerationAnimation, StatTile } from "@/components/product-console";
import type { Product, Subscription } from "@/lib/api";
import {
  createProductRun,
  getProduct,
  getSubscriptions,
  subscribeToProduct,
} from "@/lib/api";
import type { Session } from "@/lib/session";

export default function ProductDetailPage() {
  return (
    <AuthGate>
      {(session) => <ProductDetailContent session={session} />}
    </AuthGate>
  );
}

function ProductDetailContent({ session }: { session: Session }) {
  const params = useParams<{ productId: string }>();
  const router = useRouter();
  const [product, setProduct] = useState<Product | null>(null);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [rowCounts, setRowCounts] = useState<Record<string, number>>({});
  const [formats, setFormats] = useState<string[]>([]);
  const [planId, setPlanId] = useState("starter");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getProduct(params.productId), getSubscriptions(session.token)])
      .then(([nextProduct, nextSubscriptions]) => {
        setProduct(nextProduct);
        setSubscriptions(nextSubscriptions);
        setRowCounts(nextProduct.default_row_counts);
        setFormats(nextProduct.output_formats);
        setPlanId(nextProduct.plans[0]?.id ?? "starter");
      })
      .catch((caughtError) => {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load product");
      })
      .finally(() => setIsLoading(false));
  }, [params.productId, session.token]);

  const subscribed = useMemo(
    () => subscriptions.some((subscription) => subscription.product_id === product?.id),
    [subscriptions, product?.id],
  );

  const totalRows = Object.values(rowCounts).reduce((total, value) => total + Number(value || 0), 0);

  const subscribe = async () => {
    if (!product) {
      return;
    }

    setIsSubscribing(true);
    setError(null);
    try {
      const subscription = await subscribeToProduct(session.token, product.id, planId);
      setSubscriptions((current) => [
        ...current.filter((item) => item.product_id !== subscription.product_id),
        subscription,
      ]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to subscribe");
    } finally {
      setIsSubscribing(false);
    }
  };

  const generate = async () => {
    if (!product) {
      return;
    }

    setIsGenerating(true);
    setError(null);
    try {
      const run = await createProductRun(session.token, product.id, {
        row_counts: rowCounts,
        seed: `${product.id}-dashboard`,
        output_formats: Array.from(new Set(["csv", ...formats])),
      });
      router.push(`/runs/${run.run_id}?product=${product.id}`);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to generate data");
    } finally {
      setIsGenerating(false);
    }
  };

  if (isLoading || !product) {
    return (
      <div className="h-96 animate-pulse rounded-lg border border-white/10 bg-white/[0.04]" />
    );
  }

  return (
    <>
      <Link
        href="/products"
        className="mb-6 inline-flex items-center gap-2 text-sm font-semibold text-zinc-400 transition hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to products
      </Link>

      <PageHeader
        eyebrow={product.family}
        title={product.name}
        description={product.description}
        action={
          <span
            className={`rounded-md border px-3 py-2 text-xs font-semibold uppercase ${
              subscribed
                ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-200"
                : "border-amber-300/30 bg-amber-300/10 text-amber-200"
            }`}
          >
            {subscribed ? "Subscribed" : "Subscription required"}
          </span>
        }
      />

      {error ? (
        <p className="mb-6 rounded-md border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <StatTile label="Domain" value={product.domain} hint={product.module} />
        <StatTile label="Tables" value={String(product.tables.length)} hint={product.tables.join(", ")} />
        <StatTile label="Rows planned" value={String(totalRows)} hint="Editable before generation" />
      </div>

      <section className="mt-8 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
          <h2 className="text-xl font-semibold text-white">Subscription</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-500">
            Subscribe to unlock generation for this product module in the local dashboard.
          </p>
          <div className="mt-5 grid gap-3">
            {product.plans.map((plan) => (
              <button
                key={plan.id}
                className={`rounded-md border p-4 text-left transition ${
                  planId === plan.id
                    ? "border-cyan-300/40 bg-cyan-300/10"
                    : "border-white/10 bg-black/25 hover:border-white/25"
                }`}
                onClick={() => setPlanId(plan.id)}
              >
                <span className="flex items-center justify-between gap-4">
                  <span className="font-semibold text-white">{plan.name}</span>
                  <span className="text-sm font-semibold text-cyan-200">{plan.price}</span>
                </span>
                <span className="mt-2 block text-sm leading-6 text-zinc-500">{plan.description}</span>
              </button>
            ))}
          </div>
          <button
            className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-white text-sm font-semibold text-zinc-950 transition hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubscribing || subscribed}
            onClick={subscribe}
          >
            {subscribed ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : isSubscribing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Rocket className="h-4 w-4" />
            )}
            {subscribed ? "Subscribed" : "Subscribe to product"}
          </button>
        </div>

        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
          <h2 className="text-xl font-semibold text-white">Generate data</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-500">
            Configure row counts, choose output formats, then create real backend artifacts.
          </p>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {product.tables.map((table) => (
              <label key={table} className="block rounded-md border border-white/10 bg-black/25 p-3">
                <span className="text-xs font-semibold uppercase text-zinc-500">{table}</span>
                <input
                  className="mt-2 h-10 w-full rounded-md border border-white/10 bg-white/[0.04] px-3 text-sm text-white outline-none focus:border-cyan-300/50"
                  min={0}
                  max={10000}
                  type="number"
                  value={rowCounts[table] ?? 0}
                  onChange={(event) =>
                    setRowCounts((current) => ({
                      ...current,
                      [table]: Number(event.target.value),
                    }))
                  }
                />
              </label>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            {["csv", "json", "sql"].map((format) => (
              <label
                key={format}
                className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-white/10 bg-black/25 px-3 py-2 text-sm font-semibold uppercase text-zinc-300"
              >
                <input
                  checked={format === "csv" || formats.includes(format)}
                  className="accent-cyan-300"
                  disabled={format === "csv"}
                  type="checkbox"
                  onChange={(event) =>
                    setFormats((current) =>
                      event.target.checked
                        ? Array.from(new Set([...current, format]))
                        : current.filter((item) => item !== format),
                    )
                  }
                />
                {format}
              </label>
            ))}
          </div>

          <div className="mt-5">
            <GenerationAnimation active={isGenerating} />
          </div>

          <button
            className="mt-5 inline-flex h-12 w-full items-center justify-center gap-2 rounded-md bg-cyan-200 text-sm font-semibold text-zinc-950 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!subscribed || isGenerating || formats.length === 0}
            onClick={generate}
          >
            {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Rocket className="h-4 w-4" />}
            Generate and open run
          </button>
        </div>
      </section>

      <section className="mt-8 rounded-lg border border-white/10 bg-white/[0.03] p-6">
        <h2 className="text-xl font-semibold text-white">What this product includes</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {product.features.map((feature) => (
            <div key={feature} className="rounded-md border border-white/10 bg-black/25 p-4">
              <p className="text-sm leading-6 text-zinc-300">{feature}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
