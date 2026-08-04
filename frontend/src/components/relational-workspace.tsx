"use client";

import {
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Database,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  HardDrive,
  Loader2,
  MemoryStick,
  Play,
  RefreshCw,
  Rows3,
  Search,
  Send,
  Sparkles,
  Table2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { formatBytes } from "@/components/product-console";
import type {
  ArtifactList,
  GenerationRun,
  Product,
  RunArtifact,
  Subscription,
  TablePreview,
} from "@/lib/api";
import {
  apiUrl,
  createProductRun,
  getProducts,
  getRunArtifacts,
  getRuns,
  getSubscriptions,
  getTablePreview,
  subscribeToProduct,
} from "@/lib/api";
import type { Session } from "@/lib/session";

type PreviewMap = Record<string, TablePreview>;
type AgentStatus = "idle" | "subscribing" | "generating" | "complete" | "error";

export function RelationalWorkspace({ session }: { session: Session }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactList | null>(null);
  const [previews, setPreviews] = useState<PreviewMap>({});
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("Generate relational demo data with realistic keys and values");
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    loadWorkspace();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.token]);

  useEffect(() => {
    const run = runs.find((item) => item.run_id === selectedRunId);
    if (!run) {
      setArtifacts(null);
      setPreviews({});
      setSelectedTable(null);
      return;
    }
    const activeRun = run;

    setSelectedTable((current) =>
      current && activeRun.tables.some((table) => table.table_name === current)
        ? current
        : activeRun.tables[0]?.table_name ?? null,
    );

    let cancelled = false;
    async function loadRunSurface() {
      try {
        const [nextArtifacts, nextPreviews] = await Promise.all([
          getRunArtifacts(activeRun.run_id),
          Promise.all(
            activeRun.tables
              .filter((table) => table.csv_path)
              .map((table) => getTablePreview(activeRun.run_id, table.table_name, 10)),
          ),
        ]);

        if (cancelled) {
          return;
        }

        setArtifacts(nextArtifacts);
        setPreviews(
          Object.fromEntries(nextPreviews.map((preview) => [preview.table_name, preview])),
        );
      } catch (caughtError) {
        if (!cancelled) {
          setError(caughtError instanceof Error ? caughtError.message : "Unable to load run");
        }
      }
    }

    loadRunSurface();
    return () => {
      cancelled = true;
    };
  }, [runs, selectedRunId]);

  const selectedProduct = products.find((product) => product.id === selectedProductId) ?? null;
  const selectedRun = runs.find((run) => run.run_id === selectedRunId) ?? null;
  const selectedPreview = selectedTable ? previews[selectedTable] : null;
  const subscribedProductIds = useMemo(
    () => new Set(subscriptions.map((subscription) => subscription.product_id)),
    [subscriptions],
  );
  const subscribed = selectedProduct ? subscribedProductIds.has(selectedProduct.id) : false;
  const tableNames = selectedRun
    ? selectedRun.tables.map((table) => table.table_name)
    : selectedProduct?.tables ?? [];
  const visibleRows = selectedPreview?.rows ?? [];
  const agentSteps = useMemo(
    () => buildAgentSteps(status, selectedRun, selectedProduct),
    [selectedProduct, selectedRun, status],
  );
  const insight = useMemo(() => buildInsight(selectedPreview), [selectedPreview]);

  async function loadWorkspace() {
    setIsLoading(true);
    setError(null);
    try {
      const [nextProducts, nextSubscriptions, nextRuns] = await Promise.all([
        getProducts(),
        getSubscriptions(session.token),
        getRuns(),
      ]);
      const newestRuns = nextRuns.slice().reverse();
      const firstProductId =
        nextSubscriptions[0]?.product_id ?? nextProducts.find((product) => product.status === "active")?.id ?? "";
      const firstProduct = nextProducts.find((product) => product.id === firstProductId) ?? null;
      const firstRun = firstProduct
        ? newestRuns.find((run) => runMatchesProduct(run, firstProduct)) ?? newestRuns[0]
        : newestRuns[0];

      setProducts(nextProducts);
      setSubscriptions(nextSubscriptions);
      setRuns(nextRuns);
      setSelectedProductId(firstProductId);
      setSelectedRunId(firstRun?.run_id ?? null);
      setStatus(firstRun ? "complete" : "idle");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to load workspace");
      setStatus("error");
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshWorkspace() {
    setIsRefreshing(true);
    await loadWorkspace();
    setIsRefreshing(false);
  }

  async function chooseProduct(product: Product) {
    setSelectedProductId(product.id);
    const matchingRun = runs.slice().reverse().find((run) => runMatchesProduct(run, product));
    setSelectedRunId(matchingRun?.run_id ?? null);
    setStatus(matchingRun ? "complete" : "idle");
  }

  async function subscribe() {
    if (!selectedProduct) {
      return;
    }

    setStatus("subscribing");
    setError(null);
    try {
      const subscription = await subscribeToProduct(session.token, selectedProduct.id, "starter");
      setSubscriptions((current) => [
        ...current.filter((item) => item.product_id !== subscription.product_id),
        subscription,
      ]);
      setStatus("idle");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to subscribe");
      setStatus("error");
    }
  }

  async function generate() {
    if (!selectedProduct) {
      return;
    }

    setStatus("generating");
    setError(null);
    try {
      const run = await createProductRun(session.token, selectedProduct.id, {
        row_counts: selectedProduct.default_row_counts,
        seed: `${selectedProduct.id}-relational-workspace`,
        output_formats: Array.from(new Set(["csv", ...selectedProduct.output_formats])),
      });
      const nextRuns = await getRuns();
      setRuns(nextRuns);
      setSelectedRunId(run.run_id);
      setSelectedTable(run.tables[0]?.table_name ?? null);
      setStatus("complete");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to generate data");
      setStatus("error");
    }
  }

  if (isLoading) {
    return (
      <div className="grid min-h-[calc(100vh-6rem)] place-items-center rounded-lg border border-white/10 bg-zinc-950">
        <div className="flex items-center gap-3 text-sm font-semibold text-zinc-300">
          <Loader2 className="h-5 w-5 animate-spin text-cyan-200" />
          Loading DataBoom Relational
        </div>
      </div>
    );
  }

  return (
    <section className="min-h-[calc(100vh-6rem)] overflow-hidden rounded-lg border border-white/10 bg-zinc-950 shadow-2xl">
      <div className="flex min-h-[calc(100vh-6rem)] flex-col xl:grid xl:grid-cols-[16rem_minmax(0,1fr)_25rem]">
        <RelationalSidebar
          products={products}
          selectedProductId={selectedProductId}
          subscribedProductIds={subscribedProductIds}
          tableNames={tableNames}
          selectedTable={selectedTable}
          onSelectProduct={chooseProduct}
          onSelectTable={setSelectedTable}
        />

        <main className="min-w-0 border-y border-white/10 bg-zinc-100 text-zinc-950 xl:border-x xl:border-y-0">
          <WorkspaceToolbar
            run={selectedRun}
            selectedTable={selectedTable}
            artifacts={artifacts}
            isRefreshing={isRefreshing}
            onRefresh={refreshWorkspace}
          />

          {error ? (
            <div className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm font-medium text-red-700">
              {error}
            </div>
          ) : null}

          <div className="h-[calc(100vh-13rem)] min-h-[34rem] overflow-auto bg-white">
            <DataTable preview={selectedPreview} selectedTable={selectedTable} />
          </div>
        </main>

        <AgentPanel
          artifacts={artifacts}
          insight={insight}
          onGenerate={generate}
          onPromptChange={setPrompt}
          onSubscribe={subscribe}
          prompt={prompt}
          run={selectedRun}
          selectedProduct={selectedProduct}
          status={status}
          steps={agentSteps}
          subscribed={subscribed}
          visibleRows={visibleRows.length}
        />
      </div>
    </section>
  );
}

function RelationalSidebar({
  products,
  selectedProductId,
  subscribedProductIds,
  tableNames,
  selectedTable,
  onSelectProduct,
  onSelectTable,
}: {
  products: Product[];
  selectedProductId: string;
  subscribedProductIds: Set<string>;
  tableNames: string[];
  selectedTable: string | null;
  onSelectProduct: (product: Product) => void;
  onSelectTable: (tableName: string) => void;
}) {
  return (
    <aside className="bg-zinc-950 text-zinc-100">
      <div className="border-b border-white/10 px-4 py-4">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-md border border-cyan-300/25 bg-cyan-300/10">
            <Database className="h-4 w-4 text-cyan-200" />
          </span>
          <div>
            <p className="text-sm font-semibold uppercase text-white">DataBoom</p>
            <p className="text-xs text-zinc-500">Relational</p>
          </div>
        </div>
      </div>

      <div className="space-y-5 p-3">
        <div>
          <p className="px-2 text-xs font-semibold uppercase text-zinc-600">Datasets</p>
          <div className="mt-2 space-y-1">
            {products.map((product) => (
              <button
                key={product.id}
                className={`flex h-10 w-full items-center gap-2 rounded-md px-2 text-left text-sm transition ${
                  selectedProductId === product.id
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:bg-white/[0.05] hover:text-white"
                }`}
                onClick={() => onSelectProduct(product)}
              >
                <HardDrive className="h-4 w-4 shrink-0" />
                <span className="min-w-0 flex-1 truncate">{product.name}</span>
                {subscribedProductIds.has(product.id) ? (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-300" />
                ) : null}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between px-2">
            <p className="text-xs font-semibold uppercase text-zinc-600">Tables</p>
            <span className="text-xs text-zinc-600">{tableNames.length}</span>
          </div>
          <div className="mt-2 space-y-1">
            {tableNames.map((tableName) => (
              <button
                key={tableName}
                className={`flex h-9 w-full items-center gap-2 rounded-md px-2 text-left text-sm transition ${
                  selectedTable === tableName
                    ? "bg-cyan-300/15 text-cyan-100 ring-1 ring-cyan-300/25"
                    : "text-zinc-400 hover:bg-white/[0.05] hover:text-white"
                }`}
                onClick={() => onSelectTable(tableName)}
              >
                <Table2 className="h-4 w-4 shrink-0" />
                <span className="truncate">{shortTableName(tableName)}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

function WorkspaceToolbar({
  run,
  selectedTable,
  artifacts,
  isRefreshing,
  onRefresh,
}: {
  run: GenerationRun | null;
  selectedTable: string | null;
  artifacts: ArtifactList | null;
  isRefreshing: boolean;
  onRefresh: () => void;
}) {
  const table = run?.tables.find((item) => item.table_name === selectedTable);

  return (
    <header className="flex min-h-16 flex-col gap-3 border-b border-zinc-200 bg-white px-5 py-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="truncate text-xl font-semibold text-zinc-950">
            {selectedTable ? shortTableName(selectedTable) : "Relational workspace"}
          </h1>
          <span className="rounded-md bg-zinc-100 px-2 py-1 text-xs font-semibold text-zinc-500">
            {table ? `${table.row_count} records` : "No run"}
          </span>
        </div>
        <p className="mt-1 truncate text-xs text-zinc-500">
          {run ? run.run_id : "DataBoom Relational"}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <ToolbarPill active icon={Table2} label="Table" />
        <ArtifactShortcut artifacts={artifacts} extension=".json" icon={FileJson} label="JSON" />
        <ArtifactShortcut artifacts={artifacts} extension=".sql" icon={FileText} label="SQL" />
        <ToolbarPill icon={MemoryStick} label="Postgres state" />
        <button
          className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 px-3 text-sm font-semibold text-zinc-700 transition hover:border-cyan-500 hover:text-cyan-700"
          onClick={onRefresh}
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>
    </header>
  );
}

function ToolbarPill({
  active = false,
  icon: Icon,
  label,
}: {
  active?: boolean;
  icon: typeof Table2;
  label: string;
}) {
  return (
    <span
      className={`inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm font-semibold ${
        active
          ? "border-teal-600 bg-teal-600 text-white"
          : "border-zinc-200 bg-white text-zinc-700"
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </span>
  );
}

function ArtifactShortcut({
  artifacts,
  extension,
  icon: Icon,
  label,
}: {
  artifacts: ArtifactList | null;
  extension: string;
  icon: typeof FileJson;
  label: string;
}) {
  const artifact = artifacts?.files.find((file) => file.relative_path.endsWith(extension));
  const [href, setHref] = useState("#");

  useEffect(() => {
    if (!artifact) {
      setHref("#");
      return;
    }
    apiUrl(artifact.download_url).then(setHref).catch(() => setHref("#"));
  }, [artifact]);

  if (!artifact) {
    return <ToolbarPill icon={Icon} label={label} />;
  }

  return (
    <a
      className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 px-3 text-sm font-semibold text-zinc-700 transition hover:border-cyan-500 hover:text-cyan-700"
      href={href}
    >
      <Icon className="h-4 w-4" />
      {label}
    </a>
  );
}

function DataTable({
  preview,
  selectedTable,
}: {
  preview: TablePreview | null;
  selectedTable: string | null;
}) {
  if (!preview) {
    return (
      <div className="grid h-full place-items-center px-6 text-center">
        <div>
          <Rows3 className="mx-auto h-10 w-10 text-zinc-300" />
          <p className="mt-4 text-lg font-semibold text-zinc-950">
            {selectedTable ? shortTableName(selectedTable) : "No table selected"}
          </p>
          <p className="mt-2 text-sm text-zinc-500">Generate a relational run to populate this grid.</p>
        </div>
      </div>
    );
  }

  return (
    <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
      <thead className="sticky top-0 z-10 bg-zinc-50">
        <tr>
          <th className="w-14 border-b border-r border-zinc-200 px-3 py-2 text-xs font-semibold text-zinc-400">
            #
          </th>
          {preview.columns.map((column) => (
            <th
              key={column}
              className="min-w-40 border-b border-r border-zinc-200 px-3 py-2 align-bottom"
            >
              <span className="block text-sm font-semibold text-zinc-950">{column}</span>
              <span className="mt-1 block text-[0.68rem] font-semibold uppercase text-zinc-400">
                {inferColumnType(column, preview.rows)}
              </span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {preview.rows.map((row, rowIndex) => (
          <tr key={rowIndex} className="hover:bg-cyan-50/70">
            <td className="border-b border-r border-zinc-100 bg-zinc-50 px-3 py-2 text-xs font-semibold text-zinc-400">
              {rowIndex + 1}
            </td>
            {preview.columns.map((column) => (
              <td
                key={column}
                className="max-w-72 truncate border-b border-r border-zinc-100 px-3 py-2 text-zinc-700"
                title={row[column] ?? ""}
              >
                {row[column] ?? ""}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function AgentPanel({
  artifacts,
  insight,
  onGenerate,
  onPromptChange,
  onSubscribe,
  prompt,
  run,
  selectedProduct,
  status,
  steps,
  subscribed,
  visibleRows,
}: {
  artifacts: ArtifactList | null;
  insight: Insight | null;
  onGenerate: () => void;
  onPromptChange: (value: string) => void;
  onSubscribe: () => void;
  prompt: string;
  run: GenerationRun | null;
  selectedProduct: Product | null;
  status: AgentStatus;
  steps: AgentStep[];
  subscribed: boolean;
  visibleRows: number;
}) {
  const busy = status === "generating" || status === "subscribing";

  return (
    <aside className="flex min-h-full flex-col bg-zinc-50 text-zinc-950">
      <div className="border-b border-zinc-200 bg-white px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase text-zinc-400">Agent workspace</p>
            <h2 className="mt-1 truncate text-lg font-semibold text-zinc-950">
              DataBoom Relational
            </h2>
          </div>
          <span
            className={`inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs font-semibold ${
              run?.validation?.passed
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-zinc-200 bg-zinc-50 text-zinc-500"
            }`}
          >
            {run?.validation?.passed ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <CircleAlert className="h-3.5 w-3.5" />
            )}
            {run?.validation?.passed ? "Validated" : "Waiting"}
          </span>
        </div>

        <div className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-2">
          <textarea
            className="h-20 w-full resize-none bg-transparent p-2 text-sm text-zinc-800 outline-none"
            onChange={(event) => onPromptChange(event.target.value)}
            value={prompt}
          />
          <div className="flex items-center justify-between gap-3 border-t border-zinc-200 pt-2">
            <span className="inline-flex items-center gap-2 text-xs font-semibold text-zinc-500">
              <Sparkles className="h-3.5 w-3.5 text-cyan-600" />
              {selectedProduct?.name ?? "No dataset"}
            </span>
            {subscribed ? (
              <button
                className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-950 px-3 text-sm font-semibold text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={busy || !selectedProduct}
                onClick={onGenerate}
              >
                {status === "generating" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Run
              </button>
            ) : (
              <button
                className="inline-flex h-9 items-center gap-2 rounded-md bg-cyan-700 px-3 text-sm font-semibold text-white transition hover:bg-cyan-600 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={busy || !selectedProduct}
                onClick={onSubscribe}
              >
                {status === "subscribing" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Subscribe
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-950">Generation steps</h3>
            <ChevronDown className="h-4 w-4 text-zinc-400" />
          </div>
          <div className="space-y-2">
            {steps.map((step) => (
              <div key={step.label} className="rounded-md border border-zinc-200 bg-white p-3">
                <div className="flex items-start gap-3">
                  <span
                    className={`mt-0.5 grid h-5 w-5 place-items-center rounded-full ${
                      step.state === "active"
                        ? "bg-cyan-100 text-cyan-700"
                        : step.state === "done"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-zinc-100 text-zinc-400"
                    }`}
                  >
                    {step.state === "active" ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    )}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-zinc-900">{step.label}</p>
                    <p className="mt-1 text-xs leading-5 text-zinc-500">{step.detail}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <RunSummary run={run} visibleRows={visibleRows} />
        <InsightPanel insight={insight} />
        <ArtifactListPanel artifacts={artifacts} />
      </div>
    </aside>
  );
}

function RunSummary({ run, visibleRows }: { run: GenerationRun | null; visibleRows: number }) {
  if (!run) {
    return (
      <section className="rounded-md border border-zinc-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-zinc-950">Run summary</h3>
        <p className="mt-2 text-sm leading-6 text-zinc-500">No generated run selected.</p>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-zinc-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-zinc-950">Run summary</h3>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <Metric label="Rows" value={String(run.total_rows)} />
        <Metric label="Tables" value={String(run.table_count)} />
        <Metric label="Preview" value={String(visibleRows)} />
      </div>
      <div className="mt-4 space-y-2">
        {run.tables.map((table) => (
          <div key={table.table_name} className="flex items-center justify-between gap-3 text-sm">
            <span className="truncate text-zinc-600">{shortTableName(table.table_name)}</span>
            <span className="font-semibold text-zinc-950">{table.row_count}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2">
      <p className="text-[0.68rem] font-semibold uppercase text-zinc-400">{label}</p>
      <p className="mt-1 text-sm font-semibold text-zinc-950">{value}</p>
    </div>
  );
}

function InsightPanel({ insight }: { insight: Insight | null }) {
  if (!insight) {
    return (
      <section className="rounded-md border border-zinc-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-zinc-400" />
          <h3 className="text-sm font-semibold text-zinc-950">Table insight</h3>
        </div>
        <p className="mt-2 text-sm leading-6 text-zinc-500">No table distribution available.</p>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-zinc-200 bg-white p-4">
      <div className="flex items-center gap-2">
        <Search className="h-4 w-4 text-cyan-700" />
        <h3 className="text-sm font-semibold text-zinc-950">{insight.title}</h3>
      </div>
      <div className="mt-4 space-y-3">
        {insight.values.map((item) => (
          <div key={item.label}>
            <div className="mb-1 flex items-center justify-between gap-3 text-xs">
              <span className="truncate font-semibold text-zinc-600">{item.label}</span>
              <span className="text-zinc-400">{item.count}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
              <div className="h-full rounded-full bg-cyan-600" style={{ width: `${item.percent}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ArtifactListPanel({ artifacts }: { artifacts: ArtifactList | null }) {
  return (
    <section className="rounded-md border border-zinc-200 bg-white p-4">
      <div className="flex items-center gap-2">
        <Download className="h-4 w-4 text-zinc-500" />
        <h3 className="text-sm font-semibold text-zinc-950">Exports</h3>
      </div>
      <div className="mt-3 space-y-2">
        {artifacts?.files.length ? (
          artifacts.files.slice(0, 8).map((artifact) => (
            <ArtifactLink key={artifact.relative_path} artifact={artifact} />
          ))
        ) : (
          <p className="text-sm leading-6 text-zinc-500">No artifacts available.</p>
        )}
      </div>
    </section>
  );
}

function ArtifactLink({ artifact }: { artifact: RunArtifact }) {
  const [href, setHref] = useState("#");
  const Icon = artifactIcon(artifact.relative_path);

  useEffect(() => {
    apiUrl(artifact.download_url).then(setHref).catch(() => setHref("#"));
  }, [artifact.download_url]);

  return (
    <a
      className="flex items-center justify-between gap-3 rounded-md border border-zinc-200 px-3 py-2 text-sm transition hover:border-cyan-400 hover:bg-cyan-50"
      href={href}
    >
      <span className="flex min-w-0 items-center gap-2">
        <Icon className="h-4 w-4 shrink-0 text-zinc-500" />
        <span className="truncate text-zinc-700">{artifact.relative_path}</span>
      </span>
      <span className="shrink-0 text-xs font-semibold text-zinc-400">
        {formatBytes(artifact.size_bytes)}
      </span>
    </a>
  );
}

type AgentStep = {
  label: string;
  detail: string;
  state: "done" | "active" | "waiting";
};

type Insight = {
  title: string;
  values: { label: string; count: number; percent: number }[];
};

function buildAgentSteps(
  status: AgentStatus,
  run: GenerationRun | null,
  product: Product | null,
): AgentStep[] {
  const done = status === "complete" || Boolean(run);
  const active = status === "generating";
  return [
    {
      label: "Read relational schema",
      detail: product ? `${product.tables.length} tables in ${product.name}` : "Waiting for dataset",
      state: done ? "done" : active ? "active" : "waiting",
    },
    {
      label: "Resolve keys and dependencies",
      detail: "Primary keys, foreign keys, and generation order",
      state: done ? "done" : active ? "active" : "waiting",
    },
    {
      label: "Generate table rows",
      detail: run ? `${run.total_rows} rows written` : "CSV-first artifact stream",
      state: done ? "done" : active ? "active" : "waiting",
    },
    {
      label: "Validate and export",
      detail: run?.validation?.passed ? "Validation passed" : "Awaiting validation report",
      state: done && run?.validation?.passed ? "done" : active ? "active" : "waiting",
    },
  ];
}

function buildInsight(preview: TablePreview | null): Insight | null {
  if (!preview || preview.rows.length === 0) {
    return null;
  }

  const preferredColumn =
    ["status", "gender", "age", "payment_method", "payment_method_id"].find((column) =>
      preview.columns.includes(column),
    ) ?? preview.columns.find((column) => new Set(preview.rows.map((row) => row[column])).size <= 6);

  if (!preferredColumn) {
    return null;
  }

  const counts = new Map<string, number>();
  for (const row of preview.rows) {
    const label = bucketValue(preferredColumn, row[preferredColumn] ?? "empty");
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }

  const total = preview.rows.length;
  return {
    title: `${shortTableName(preview.table_name)} by ${preferredColumn}`,
    values: Array.from(counts.entries()).map(([label, count]) => ({
      label,
      count,
      percent: Math.max(4, Math.round((count / total) * 100)),
    })),
  };
}

function bucketValue(column: string, value: string) {
  if (column !== "age") {
    return value;
  }

  const age = Number(value);
  if (Number.isNaN(age)) {
    return value;
  }
  if (age <= 25) {
    return "18-25";
  }
  if (age <= 35) {
    return "26-35";
  }
  if (age <= 45) {
    return "36-45";
  }
  if (age <= 55) {
    return "46-55";
  }
  return "56+";
}

function inferColumnType(column: string, rows: Record<string, string>[]) {
  const sample = rows.find((row) => row[column])?.[column] ?? "";
  if (/^\d+$/.test(sample)) {
    return "integer";
  }
  if (/^\d+\.\d+$/.test(sample)) {
    return "real";
  }
  if (/^\d{4}-\d{2}-\d{2}/.test(sample)) {
    return "timestamp";
  }
  return "text";
}

function runMatchesProduct(run: GenerationRun, product: Product) {
  const runTables = new Set(run.tables.map((table) => shortTableName(table.table_name)));
  return product.tables.some((table) => runTables.has(table));
}

function shortTableName(tableName: string) {
  return tableName.includes(".") ? tableName.split(".").at(-1) ?? tableName : tableName;
}

function artifactIcon(path: string) {
  if (path.endsWith(".csv")) {
    return FileSpreadsheet;
  }
  if (path.endsWith(".json")) {
    return FileJson;
  }
  return FileText;
}
