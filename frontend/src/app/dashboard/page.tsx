"use client";

import { ArrowRight, Database, PlayCircle } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { EmptyState, ProductCard, StatTile } from "@/components/product-console";
import type { GenerationRun, Product, Subscription } from "@/lib/api";
import { getProducts, getRuns, getSubscriptions } from "@/lib/api";
import type { Session } from "@/lib/session";

export default function DashboardPage() {
  return (
    <AuthGate>
      {(session) => <DashboardContent session={session} />}
    </AuthGate>
  );
}

function DashboardContent({ session }: { session: Session }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([getProducts(), getSubscriptions(session.token), getRuns()])
      .then(([nextProducts, nextSubscriptions, nextRuns]) => {
        setProducts(nextProducts);
        setSubscriptions(nextSubscriptions);
        setRuns(nextRuns);
      })
      .catch((caughtError) => {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load dashboard");
      })
      .finally(() => setIsLoading(false));
  }, [session.token]);

  const subscribedIds = useMemo(
    () => new Set(subscriptions.map((subscription) => subscription.product_id)),
    [subscriptions],
  );
  const subscribedProducts = products.filter((product) => subscribedIds.has(product.id));
  const recentRuns = runs.slice(-5).reverse();

  return (
    <>
      <PageHeader
        eyebrow="Dashboard"
        title="Your DataBoom command center."
        description="Subscribe to product modules, generate realistic datasets, preview output rows, and download artifacts from the backend."
        action={
          <Link
            href="/products"
            className="inline-flex h-11 items-center gap-2 rounded-md bg-white px-5 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-100"
          >
            Browse products <ArrowRight className="h-4 w-4" />
          </Link>
        }
      />

      {error ? (
        <p className="mb-6 rounded-md border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <StatTile
          label="Subscribed products"
          value={String(subscriptions.length)}
          hint="Modules you can generate from"
        />
        <StatTile label="Available products" value={String(products.length)} hint="Generator catalog" />
        <StatTile label="Recent runs" value={String(runs.length)} hint="Current backend process" />
      </div>

      <section className="mt-8 grid gap-6 xl:grid-cols-[1fr_0.8fr]">
        <div>
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="text-xl font-semibold text-white">Subscribed products</h2>
            <Link href="/products" className="text-sm font-semibold text-cyan-200">
              Manage subscriptions
            </Link>
          </div>
          {isLoading ? (
            <LoadingRows />
          ) : subscribedProducts.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {subscribedProducts.map((product) => (
                <ProductCard key={product.id} product={product} subscribed />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No products subscribed yet"
              detail="Open Products, subscribe to a module, then generate data."
            />
          )}
        </div>

        <div>
          <h2 className="mb-4 text-xl font-semibold text-white">Recent generation runs</h2>
          <div className="space-y-3">
            {recentRuns.length > 0 ? (
              recentRuns.map((run) => (
                <Link
                  key={run.run_id}
                  href={`/runs/${run.run_id}`}
                  className="flex items-center justify-between gap-4 rounded-lg border border-white/10 bg-white/[0.03] p-4 transition hover:border-cyan-300/35 hover:bg-white/[0.06]"
                >
                  <span className="flex min-w-0 items-center gap-3">
                    <PlayCircle className="h-5 w-5 shrink-0 text-cyan-200" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-white">
                        {run.run_id}
                      </span>
                      <span className="text-xs text-zinc-500">
                        {run.total_rows} rows · {run.table_count} tables
                      </span>
                    </span>
                  </span>
                  <ArrowRight className="h-4 w-4 text-zinc-500" />
                </Link>
              ))
            ) : (
              <EmptyState
                title="No runs yet"
                detail="Generate from a subscribed product to see run output here."
              />
            )}
          </div>
        </div>
      </section>

      <section className="mt-8 rounded-lg border border-white/10 bg-white/[0.03] p-6">
        <div className="flex items-start gap-4">
          <Database className="mt-1 h-5 w-5 text-emerald-200" />
          <div>
            <h2 className="text-xl font-semibold text-white">How the flow works</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-zinc-400">
              The dashboard talks to FastAPI for login, product catalog, subscription state, generation runs,
              table previews, and artifact downloads. This is still a local MVP, but the flow is now genuinely
              full stack.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}

function LoadingRows() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {[1, 2].map((item) => (
        <div key={item} className="h-64 animate-pulse rounded-lg border border-white/10 bg-white/[0.04]" />
      ))}
    </div>
  );
}
