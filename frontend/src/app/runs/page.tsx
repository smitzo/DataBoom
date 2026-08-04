"use client";

import { ArrowRight, Clock3 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { EmptyState, StatTile } from "@/components/product-console";
import type { GenerationRun } from "@/lib/api";
import { getRuns } from "@/lib/api";

export default function RunsPage() {
  return (
    <AuthGate>
      {() => <RunsContent />}
    </AuthGate>
  );
}

function RunsContent() {
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRuns()
      .then((nextRuns) => setRuns(nextRuns.slice().reverse()))
      .catch((caughtError) => {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load runs");
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <>
      <PageHeader
        eyebrow="Runs"
        title="Generation run history."
        description="Open a generation run to preview tables or documents and download artifacts."
      />

      {error ? (
        <p className="mb-6 rounded-md border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
          {error}
        </p>
      ) : null}

      <div className="mb-8 grid gap-4 md:grid-cols-3">
        <StatTile label="Runs" value={String(runs.length)} hint="Visible backend metadata" />
        <StatTile
          label="Rows generated"
          value={String(runs.reduce((total, run) => total + run.total_rows, 0))}
          hint="Across visible runs"
        />
        <StatTile
          label="Passed validation"
          value={String(runs.filter((run) => run.validation?.passed).length)}
          hint="Runs with clean reports"
        />
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((item) => (
            <div key={item} className="h-20 animate-pulse rounded-lg border border-white/10 bg-white/[0.04]" />
          ))}
        </div>
      ) : runs.length > 0 ? (
        <div className="space-y-3">
          {runs.map((run) => (
            <Link
              key={run.run_id}
              href={`/runs/${run.run_id}`}
              className="flex items-center justify-between gap-4 rounded-lg border border-white/10 bg-white/[0.03] p-5 transition hover:border-cyan-300/35 hover:bg-white/[0.06]"
            >
              <span className="flex min-w-0 items-center gap-4">
                <Clock3 className="h-5 w-5 shrink-0 text-cyan-200" />
                <span className="min-w-0">
                  <span className="block truncate font-semibold text-white">{run.run_id}</span>
                  <span className="text-sm text-zinc-500">
                    {run.total_rows} rows · {run.table_count} tables · {run.status}
                  </span>
                </span>
              </span>
              <ArrowRight className="h-4 w-4 text-zinc-500" />
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No generation runs yet"
          detail="Subscribe to a product and generate data to create a run."
        />
      )}
    </>
  );
}
