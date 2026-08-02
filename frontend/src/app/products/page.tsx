"use client";

import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { ProductCard } from "@/components/product-console";
import type { Product, Subscription } from "@/lib/api";
import { getProducts, getSubscriptions } from "@/lib/api";
import type { Session } from "@/lib/session";

export default function ProductsPage() {
  return (
    <AuthGate>
      {(session) => <ProductsContent session={session} />}
    </AuthGate>
  );
}

function ProductsContent({ session }: { session: Session }) {
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
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load products");
      })
      .finally(() => setIsLoading(false));
  }, [session.token]);

  const subscribedIds = useMemo(
    () => new Set(subscriptions.map((subscription) => subscription.product_id)),
    [subscriptions],
  );

  return (
    <>
      <PageHeader
        eyebrow="Products"
        title="Subscribe to product modules."
        description="Pick the DataBoom product shape you need, subscribe to it, then generate data from the product page."
      />

      {error ? (
        <p className="mb-6 rounded-md border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
          {error}
        </p>
      ) : null}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <div key={item} className="h-80 animate-pulse rounded-lg border border-white/10 bg-white/[0.04]" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              subscribed={subscribedIds.has(product.id)}
            />
          ))}
        </div>
      )}
    </>
  );
}
