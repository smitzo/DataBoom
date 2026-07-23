"use client";

import { Activity, AlertCircle, CheckCircle2, Play } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

type ApiHealth = {
  status: string;
  service: string;
  version: string;
  environment: string;
  artifact_root: string;
};

type ApiRun = {
  run_id: string;
  status: "completed" | "failed";
  total_rows: number;
  table_count: number;
  artifact_dir: string;
  validation?: {
    passed: boolean;
  } | null;
};

const demoRequest = {
  schema_ddl: `
    CREATE TABLE accounts (
      id bigint PRIMARY KEY,
      name text NOT NULL
    );

    CREATE TABLE users (
      id bigint PRIMARY KEY,
      account_id bigint NOT NULL REFERENCES accounts(id),
      email text NOT NULL
    );
  `,
  row_counts: { accounts: 2, users: 3 },
  seed: "frontend-api-demo",
  domain: "general",
  output_formats: ["csv", "json"],
};

export function ApiRunPanel() {
  const apiBaseUrl = useMemo(
    () => process.env.NEXT_PUBLIC_BOOM_DATA_API_URL ?? "http://localhost:8000",
    [],
  );
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [runs, setRuns] = useState<ApiRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshApiState = useCallback(async () => {
    setError(null);
    const [healthResponse, runsResponse] = await Promise.all([
      fetch(`${apiBaseUrl}/health`, { cache: "no-store" }),
      fetch(`${apiBaseUrl}/runs`, { cache: "no-store" }),
    ]);

    if (!healthResponse.ok) {
      throw new Error("API health check failed");
    }
    if (!runsResponse.ok) {
      throw new Error("API run list failed");
    }

    setHealth((await healthResponse.json()) as ApiHealth);
    setRuns((await runsResponse.json()) as ApiRun[]);
  }, [apiBaseUrl]);

  useEffect(() => {
    refreshApiState()
      .catch((caughtError: unknown) => {
        setError(caughtError instanceof Error ? caughtError.message : "API is unavailable");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [refreshApiState]);

  const createDemoRun = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(demoRequest),
      });

      if (!response.ok) {
        throw new Error("Demo generation run failed");
      }

      const run = (await response.json()) as ApiRun;
      setRuns((currentRuns) => [...currentRuns, run]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to create run");
    } finally {
      setIsRunning(false);
    }
  };

  const latestRun = runs.at(-1);
  const online = health?.status === "ok" && error === null;

  return (
    <div className="mt-4 rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-4">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <div className="flex items-center gap-2">
            {online ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-300" />
            ) : (
              <AlertCircle className="h-5 w-5 text-amber-200" />
            )}
            <p className="text-sm font-semibold text-white">Live API bridge</p>
          </div>
          <p className="mt-2 text-sm text-zinc-400">
            {isLoading
              ? "Checking local API..."
              : online
                ? `${health.service} ${health.version} in ${health.environment}`
                : error ?? "API is unavailable"}
          </p>
        </div>

        <button
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-white px-4 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isRunning}
          onClick={createDemoRun}
        >
          {isRunning ? <Activity className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Run API demo
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <ApiStat label="Runs" value={String(runs.length)} />
        <ApiStat label="Latest rows" value={latestRun ? String(latestRun.total_rows) : "-"} />
        <ApiStat
          label="Validation"
          value={latestRun?.validation?.passed ? "Passed" : latestRun ? "Failed" : "-"}
          success={latestRun?.validation?.passed}
        />
      </div>
    </div>
  );
}

function ApiStat({
  label,
  value,
  success = false,
}: {
  label: string;
  value: string;
  success?: boolean;
}) {
  return (
    <div className="rounded-md border border-white/10 bg-black/25 px-3 py-3">
      <p className="text-xs font-semibold uppercase text-zinc-500">{label}</p>
      <p
        className={
          success
            ? "mt-2 text-sm font-semibold text-emerald-300"
            : "mt-2 text-sm font-semibold text-white"
        }
      >
        {value}
      </p>
    </div>
  );
}
