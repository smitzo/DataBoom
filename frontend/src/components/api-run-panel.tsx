"use client";

import { Activity, AlertCircle, CheckCircle2, Download, FileDown, Play, Table2 } from "lucide-react";
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
  output_formats: string[];
  tables: ApiTable[];
  validation?: {
    passed: boolean;
  } | null;
};

type ApiTable = {
  table_name: string;
  row_count: number;
};

type ApiArtifact = {
  name: string;
  relative_path: string;
  size_bytes: number;
  media_type: string;
  download_url: string;
};

type ApiArtifactList = {
  run_id: string;
  artifact_dir: string;
  files: ApiArtifact[];
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
  const apiBaseCandidates = useMemo(() => {
    const configuredUrl = process.env.NEXT_PUBLIC_DATABOOM_API_URL;
    return Array.from(
      new Set(
        [configuredUrl, "http://localhost:8001", "http://localhost:8000"].filter(
          (url): url is string => Boolean(url),
        ),
      ),
    );
  }, []);
  const [apiBaseUrl, setApiBaseUrl] = useState(apiBaseCandidates[0] ?? "http://localhost:8001");
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [runs, setRuns] = useState<ApiRun[]>([]);
  const [artifacts, setArtifacts] = useState<ApiArtifactList | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchArtifacts = useCallback(
    async (baseUrl: string, runId: string) => {
      const response = await fetch(`${baseUrl}/runs/${runId}/artifacts`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("API artifact list failed");
      }
      return (await response.json()) as ApiArtifactList;
    },
    [],
  );

  const refreshApiState = useCallback(async () => {
    setError(null);
    let lastError: Error | null = null;

    for (const candidateUrl of apiBaseCandidates) {
      try {
        const [healthResponse, runsResponse] = await Promise.all([
          fetch(`${candidateUrl}/health`, { cache: "no-store" }),
          fetch(`${candidateUrl}/runs`, { cache: "no-store" }),
        ]);

        if (!healthResponse.ok) {
          throw new Error("API health check failed");
        }
        if (!runsResponse.ok) {
          throw new Error("API run list failed");
        }

        const nextRuns = (await runsResponse.json()) as ApiRun[];
        const latest = nextRuns.at(-1);

        setApiBaseUrl(candidateUrl);
        setHealth((await healthResponse.json()) as ApiHealth);
        setRuns(nextRuns);
        setArtifacts(latest ? await fetchArtifacts(candidateUrl, latest.run_id) : null);
        return;
      } catch (caughtError) {
        lastError = caughtError instanceof Error ? caughtError : new Error("API is unavailable");
      }
    }

    throw lastError ?? new Error("API is unavailable");
  }, [apiBaseCandidates, fetchArtifacts]);

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
      setArtifacts(await fetchArtifacts(apiBaseUrl, run.run_id));
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
                ? `${health.service} ${health.version} in ${health.environment} at ${apiBaseUrl}`
                : error ?? "API is unavailable"}
          </p>
        </div>

        <button
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-white px-4 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isRunning || isLoading || !online}
          onClick={createDemoRun}
        >
          {isRunning ? <Activity className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Generate sample data
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

      {latestRun ? (
        <div className="mt-4 grid gap-3 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-md border border-white/10 bg-black/25 p-4">
            <div className="flex items-center gap-2">
              <Table2 className="h-4 w-4 text-cyan-200" />
              <p className="text-sm font-semibold text-white">Generated tables</p>
            </div>
            <div className="mt-3 space-y-2">
              {latestRun.tables.map((table) => (
                <div
                  key={table.table_name}
                  className="flex items-center justify-between gap-3 rounded-md bg-white/[0.04] px-3 py-2"
                >
                  <span className="truncate text-sm text-zinc-300">{table.table_name}</span>
                  <span className="text-xs font-semibold uppercase text-cyan-200">
                    {table.row_count} rows
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-md border border-white/10 bg-black/25 p-4">
            <div className="flex items-center gap-2">
              <FileDown className="h-4 w-4 text-emerald-200" />
              <p className="text-sm font-semibold text-white">Output artifacts</p>
            </div>
            <div className="mt-3 max-h-44 space-y-2 overflow-y-auto pr-1">
              {artifacts?.files.map((artifact) => (
                <a
                  key={artifact.relative_path}
                  className="flex items-center justify-between gap-3 rounded-md bg-white/[0.04] px-3 py-2 text-sm transition hover:bg-white/[0.08]"
                  href={`${apiBaseUrl}${artifact.download_url}`}
                >
                  <span className="min-w-0 truncate text-zinc-300">{artifact.relative_path}</span>
                  <span className="inline-flex shrink-0 items-center gap-2 text-xs font-semibold uppercase text-emerald-200">
                    {formatBytes(artifact.size_bytes)}
                    <Download className="h-3.5 w-3.5" />
                  </span>
                </a>
              )) ?? <p className="text-sm text-zinc-500">Artifacts will appear after generation.</p>}
            </div>
          </div>
        </div>
      ) : null}
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

function formatBytes(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  return `${(sizeBytes / 1024).toFixed(1)} KB`;
}
