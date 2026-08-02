"use client";

import { ArrowRight, PackageCheck, Settings } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { EmptyState, StatTile } from "@/components/product-console";
import type { Product, Subscription } from "@/lib/api";
import { getProducts, getSubscriptions } from "@/lib/api";
import type { Session } from "@/lib/session";

export default function SubscriptionSettingsPage() {
  return (
    <AuthGate>
      {(session) => <SubscriptionSettingsContent session={session} />}
    </AuthGate>
  );
}

function SubscriptionSettingsContent({ session }: { session: Session }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getProducts(), getSubscriptions(session.token)])
      .then(([nextProducts, nextSubscriptions]) => {
        setProducts(nextProducts);
        setSubscriptions(nextSubscriptions);
      })
      .catch((caughtError) => {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load subscriptions");
      })
      .finally(() => setIsLoading(false));
  }, [session.token]);

  const productById = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  );
  const subscribedIds = new Set(subscriptions.map((subscription) => subscription.product_id));
  const availableProducts = products.filter((product) => !subscribedIds.has(product.id));

  return (
    <>
      <PageHeader
        eyebrow="Settings"
        title="My subscriptions"
        description="Manage which DataBoom product modules are active for your local workspace."
      />

      {error ? (
        <p className="mb-6 rounded-md border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <StatTile
          label="Active subscriptions"
          value={String(subscriptions.length)}
          hint="Products unlocked"
        />
        <StatTile
          label="Available modules"
          value={String(products.length)}
          hint="Generator catalog"
        />
        <StatTile
          label="Billing mode"
          value="Demo"
          hint="Local in-memory state"
        />
      </div>

      <section className="mt-8 grid gap-6 xl:grid-cols-[1fr_0.8fr]">
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
          <div className="mb-5 flex items-center gap-3">
            <Settings className="h-5 w-5 text-cyan-200" />
            <h2 className="text-xl font-semibold text-white">Active product subscriptions</h2>
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2].map((item) => (
                <div
                  key={item}
                  className="h-24 animate-pulse rounded-md border border-white/10 bg-white/[0.04]"
                />
              ))}
            </div>
          ) : subscriptions.length > 0 ? (
            <div className="space-y-3">
              {subscriptions.map((subscription) => {
                const product = productById.get(subscription.product_id);
                return (
                  <div
                    key={subscription.subscription_id}
                    className="rounded-md border border-white/10 bg-black/25 p-4"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="font-semibold text-white">
                          {product?.name ?? subscription.product_id}
                        </p>
                        <p className="mt-1 text-sm text-zinc-500">
                          {subscription.plan_id} plan · {subscription.status}
                        </p>
                      </div>
                      <Link
                        href={`/products/${subscription.product_id}`}
                        className="inline-flex h-10 items-center gap-2 rounded-md border border-white/10 px-3 text-sm font-semibold text-zinc-200 transition hover:border-cyan-300/35 hover:text-cyan-100"
                      >
                        Open product
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState
              title="No subscriptions yet"
              detail="Open an available product below, subscribe, then come back here to manage it."
            />
          )}
        </div>

        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
          <div className="mb-5 flex items-center gap-3">
            <PackageCheck className="h-5 w-5 text-emerald-200" />
            <h2 className="text-xl font-semibold text-white">Available to subscribe</h2>
          </div>

          <div className="space-y-3">
            {availableProducts.map((product) => (
              <Link
                key={product.id}
                href={`/products/${product.id}`}
                className="flex items-center justify-between gap-4 rounded-md border border-white/10 bg-black/25 p-4 transition hover:border-emerald-300/35 hover:bg-white/[0.05]"
              >
                <span>
                  <span className="block font-semibold text-white">{product.name}</span>
                  <span className="text-sm text-zinc-500">{product.module}</span>
                </span>
                <ArrowRight className="h-4 w-4 text-zinc-500" />
              </Link>
            ))}
            {!isLoading && availableProducts.length === 0 ? (
              <p className="rounded-md border border-emerald-300/20 bg-emerald-300/10 p-4 text-sm text-emerald-100">
                You are subscribed to every active demo product.
              </p>
            ) : null}
          </div>
        </div>
      </section>
    </>
  );
}
