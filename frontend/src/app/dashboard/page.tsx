"use client";

import { ArrowRight, CheckCircle2, Clock3, Settings } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { EmptyState, StatTile } from "@/components/product-console";
import type { GenerationRun, Subscription } from "@/lib/api";
import { getRuns, getSubscriptions } from "@/lib/api";
import type { Session } from "@/lib/session";

export default function DashboardPage() {
  return (
    <AuthGate>
      {(session) => <DashboardContent session={session} />}
    </AuthGate>
  );
}

function DashboardContent({ session }: { session: Session }) {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([getSubscriptions(session.token), getRuns()])
      .then(([nextSubscriptions, nextRuns]) => {
        setSubscriptions(nextSubscriptions);
        setRuns(nextRuns);
      })
      .catch((caughtError) => {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load dashboard");
      })
      .finally(() => setIsLoading(false));
  }, [session.token]);

  const recentRuns = runs.slice(-6).reverse();
  const totalRows = useMemo(
    () => runs.reduce((total, run) => total + run.total_rows, 0),
    [runs],
  );
  const passedRuns = runs.filter((run) => run.validation?.passed).length;

  return (
    <>
      <PageHeader
        eyebrow="My dashboard"
        title="A clean view of your DataBoom workspace."
        description="Track generated runs, validation health, and workspace state without mixing subscription settings into the main dashboard."
      />

      {error ? (
        <p className="mb-6 rounded-md border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
          {error}
        </p>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Generation runs" value={String(runs.length)} hint="Current API process" />
        <StatTile label="Rows generated" value={String(totalRows)} hint="Across visible runs" />
        <StatTile label="Validation passed" value={String(passedRuns)} hint="Runs with clean reports" />
        <StatTile
          label="Subscriptions"
          value={String(subscriptions.length)}
          hint="Managed in settings"
        />
      </div>

      <section className="mt-8 grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">Recent generation runs</h2>
              <p className="mt-1 text-sm text-zinc-500">
                Open a run to preview top rows and download generated artifacts.
              </p>
            </div>
            <Link href="/runs" className="text-sm font-semibold text-cyan-200">
              View all runs
            </Link>
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((item) => (
                <div
                  key={item}
                  className="h-20 animate-pulse rounded-md border border-white/10 bg-white/[0.04]"
                />
              ))}
            </div>
          ) : recentRuns.length > 0 ? (
            <div className="space-y-3">
              {recentRuns.map((run) => (
                <Link
                  key={run.run_id}
                  href={`/runs/${run.run_id}`}
                  className="grid gap-4 rounded-md border border-white/10 bg-black/25 p-4 transition hover:border-cyan-300/35 hover:bg-white/[0.05] md:grid-cols-[1fr_auto]"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-3">
                      <Clock3 className="h-4 w-4 shrink-0 text-cyan-200" />
                      <p className="truncate text-sm font-semibold text-white">{run.run_id}</p>
                    </div>
                    <p className="mt-2 text-sm text-zinc-500">
                      {run.total_rows} rows · {run.table_count} tables · {run.domain}
                    </p>
                  </div>
                  <span className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-200">
                    Open <ArrowRight className="h-4 w-4" />
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No runs yet"
              detail="Generate data from a subscribed product to see output here."
            />
          )}
        </div>

        <aside className="space-y-6">
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
            <div className="flex items-start gap-3">
              <Settings className="mt-1 h-5 w-5 text-cyan-200" />
              <div>
                <h2 className="text-xl font-semibold text-white">My subscriptions</h2>
                <p className="mt-2 text-sm leading-6 text-zinc-500">
                  Product subscription details live in settings so the dashboard stays focused.
                </p>
              </div>
            </div>
            <Link
              href="/settings/subscriptions"
              className="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md border border-white/10 text-sm font-semibold text-zinc-200 transition hover:border-cyan-300/35 hover:text-cyan-100"
            >
              Open subscription settings
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="rounded-lg border border-emerald-300/20 bg-emerald-300/10 p-5">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-emerald-200" />
              <h2 className="text-lg font-semibold text-white">Backend connected</h2>
            </div>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              This dashboard reads runs and subscriptions from the FastAPI service, not static mock data.
            </p>
          </div>
        </aside>
      </section>
    </>
  );
}
