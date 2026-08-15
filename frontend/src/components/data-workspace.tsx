"use client";

import {
  BarChart3,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Clock3,
  Database,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  HardDrive,
  Layers3,
  Loader2,
  PackageCheck,
  PanelLeftClose,
  PanelLeftOpen,
  Play,
  RefreshCw,
  Rows3,
  Search,
  Send,
  Sparkles,
  Table2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { formatBytes } from "@/components/product-console";
import type {
  ArtifactList,
  DocumentPreview,
  GenerationRun,
  Product,
  RunArtifact,
  Subscription,
  TablePreview,
} from "@/lib/api";
import {
  apiUrl,
  createAsyncProductRun,
  getDocumentPreview,
  getProducts,
  getRun,
  getRunArtifacts,
  getRuns,
  getSubscriptions,
  getTablePreview,
  subscribeToProduct,
} from "@/lib/api";
import type { Session } from "@/lib/session";

type PreviewMap = Record<string, TablePreview>;
type DocumentPreviewMap = Record<string, DocumentPreview>;
type AgentStatus = "idle" | "subscribing" | "generating" | "complete" | "error";

export function DataWorkspace({ session }: { session: Session }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactList | null>(null);
  const [previews, setPreviews] = useState<PreviewMap>({});
  const [documentPreviews, setDocumentPreviews] = useState<DocumentPreviewMap>({});
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedResource, setSelectedResource] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("Generate realistic data for the selected product");
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isWorkspaceRailCollapsed, setIsWorkspaceRailCollapsed] = useState(false);

  useEffect(() => {
    loadWorkspace();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.token]);

  useEffect(() => {
    const run = runs.find((item) => item.run_id === selectedRunId);
    if (!run) {
      setArtifacts(null);
      setPreviews({});
      setDocumentPreviews({});
      return;
    }
    const activeRun = run;

    setSelectedResource((current) =>
      current && runResources(activeRun).includes(current)
        ? current
        : runResources(activeRun)[0] ?? null,
    );

    let cancelled = false;
    async function loadRunSurface() {
      const [nextArtifacts, nextTablePreviews, nextDocumentPreviews] = await Promise.all([
        getRunArtifacts(activeRun.run_id).catch(() => null),
        activeRun.kind === "relational"
          ? Promise.all(
              activeRun.tables
                .filter((table) => table.csv_path)
                .map((table) => loadTablePreviewSafe(activeRun.run_id, table.table_name)),
            )
          : Promise.resolve([]),
        activeRun.kind === "document"
          ? Promise.all(
              activeRun.collections
                .filter((collection) => collection.json_path)
                .map((collection) =>
                  loadDocumentPreviewSafe(activeRun.run_id, collection.collection_name),
                ),
            )
          : Promise.resolve([]),
      ]);

      if (cancelled) {
        return;
      }

      setArtifacts(nextArtifacts);
      setPreviews(
        Object.fromEntries(
          nextTablePreviews
            .filter((preview): preview is TablePreview => Boolean(preview))
            .map((preview) => [preview.table_name, preview]),
        ),
      );
      setDocumentPreviews(
        Object.fromEntries(
          nextDocumentPreviews
            .filter((preview): preview is DocumentPreview => Boolean(preview))
            .map((preview) => [preview.collection_name, preview]),
        ),
      );
    }

    loadRunSurface();
    return () => {
      cancelled = true;
    };
  }, [runs, selectedRunId]);

  useEffect(() => {
    const run = runs.find((item) => item.run_id === selectedRunId);
    if (!run || run.status !== "running") {
      return;
    }

    const runId = run.run_id;
    let cancelled = false;
    setStatus("generating");

    async function pollRun() {
      while (!cancelled) {
        await delay(1_000);
        const nextRun = await getRun(runId);

        if (cancelled) {
          return;
        }

        setRuns((current) => upsertRun(current, nextRun));
        setSelectedResource((current) =>
          current && runResources(nextRun).includes(current)
            ? current
            : runResources(nextRun)[0] ?? null,
        );

        if (nextRun.status !== "running") {
          setStatus(runAgentStatus(nextRun));
          if (nextRun.status === "failed") {
            setError(nextRun.error ?? "Generation failed");
          }
          return;
        }
      }
    }

    pollRun().catch((caughtError) => {
      if (!cancelled) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to poll generation");
        setStatus("error");
      }
    });

    return () => {
      cancelled = true;
    };
  }, [runs, selectedRunId]);

  const selectedProduct = products.find((product) => product.id === selectedProductId) ?? null;
  const selectedRun = runs.find((run) => run.run_id === selectedRunId) ?? null;
  const selectedTablePreview = selectedResource ? previews[selectedResource] : null;
  const selectedDocumentPreview = selectedResource ? documentPreviews[selectedResource] : null;
  const subscribedProductIds = useMemo(
    () => new Set(subscriptions.map((subscription) => subscription.product_id)),
    [subscriptions],
  );
  const subscribed = selectedProduct ? subscribedProductIds.has(selectedProduct.id) : false;
  const activeKind = selectedRun?.kind ?? selectedProduct?.kind ?? "relational";
  const resourceNames = selectedRun ? runResources(selectedRun) : productResources(selectedProduct);
  const visibleRows = selectedTablePreview?.rows.length ?? selectedDocumentPreview?.documents.length ?? 0;
  const agentSteps = useMemo(
    () => buildAgentSteps(status, selectedRun, selectedProduct),
    [selectedProduct, selectedRun, status],
  );
  const insight = useMemo(
    () => buildInsight(selectedTablePreview, selectedDocumentPreview),
    [selectedDocumentPreview, selectedTablePreview],
  );
  const workspaceGridClass = isWorkspaceRailCollapsed
    ? "flex min-h-[calc(100vh-5.5rem)] flex-col xl:grid xl:grid-cols-[4.75rem_minmax(0,1fr)_21rem]"
    : "flex min-h-[calc(100vh-5.5rem)] flex-col xl:grid xl:grid-cols-[15rem_minmax(0,1fr)_21rem]";

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
      const activeProductIds = new Set(nextProducts.map((product) => product.id));
      const firstSubscribedProductId = nextSubscriptions.find((subscription) =>
        activeProductIds.has(subscription.product_id),
      )?.product_id;
      const firstProductId =
        firstSubscribedProductId ??
        nextProducts.find((product) => product.status === "active")?.id ??
        nextProducts[0]?.id ??
        "";
      const firstProduct = nextProducts.find((product) => product.id === firstProductId) ?? null;
      const firstRun = firstProduct
        ? newestRuns.find((run) => runMatchesProduct(run, firstProduct))
        : newestRuns[0];

      setProducts(nextProducts);
      setSubscriptions(nextSubscriptions);
      setRuns(nextRuns);
      setSelectedProductId(firstProductId);
      setSelectedRunId(firstRun?.run_id ?? null);
      setSelectedResource(
        firstRun ? runResources(firstRun)[0] ?? null : productResources(firstProduct)[0] ?? null,
      );
      setStatus(firstRun ? runAgentStatus(firstRun) : "idle");
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
    setSelectedResource(
      matchingRun ? runResources(matchingRun)[0] ?? null : productResources(product)[0] ?? null,
    );
    setStatus(matchingRun ? runAgentStatus(matchingRun) : "idle");
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
    if (selectedProduct.status !== "active") {
      setError(`${selectedProduct.name} is planned and is not runnable yet`);
      return;
    }

    setStatus("generating");
    setError(null);
    try {
      const run = await createAsyncProductRun(session.token, selectedProduct.id, {
        row_counts: selectedProduct.default_row_counts,
        seed: `${selectedProduct.id}-workspace`,
        output_formats: selectedProduct.output_formats,
      });
      setRuns((current) => upsertRun(current, run));
      setSelectedRunId(run.run_id);
      setSelectedResource(runResources(run)[0] ?? null);
      setStatus(runAgentStatus(run));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to generate data");
      setStatus("error");
    }
  }

  if (isLoading) {
    return (
      <div className="grid min-h-[calc(100vh-6rem)] place-items-center rounded-xl border border-white/10 bg-zinc-950">
        <div className="flex items-center gap-3 text-sm font-semibold text-zinc-300">
          <Loader2 className="h-5 w-5 animate-spin text-cyan-200" />
          Loading DataBoom Workspace
        </div>
      </div>
    );
  }

  return (
    <section className="min-h-[calc(100vh-5.5rem)] overflow-hidden rounded-2xl border border-white/10 bg-zinc-950 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
      <div className={workspaceGridClass}>
        <WorkspaceSidebar
          activeKind={activeKind}
          collapsed={isWorkspaceRailCollapsed}
          onToggleCollapse={() => setIsWorkspaceRailCollapsed((current) => !current)}
          products={products}
          selectedProductId={selectedProductId}
          subscribedProductIds={subscribedProductIds}
          resourceNames={resourceNames}
          selectedResource={selectedResource}
          onSelectProduct={chooseProduct}
          onSelectResource={setSelectedResource}
        />

        <main className="min-w-0 border-y border-white/10 bg-zinc-100 text-zinc-950 xl:border-x xl:border-y-0">
          <WorkspaceOverview
            artifacts={artifacts}
            product={selectedProduct}
            run={selectedRun}
            subscribed={subscribed}
            visibleRows={visibleRows}
          />
          <WorkspaceToolbar
            run={selectedRun}
            activeKind={activeKind}
            selectedResource={selectedResource}
            artifacts={artifacts}
            isRefreshing={isRefreshing}
            onRefresh={refreshWorkspace}
          />

          {error ? (
            <div className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm font-medium text-red-700">
              {error}
            </div>
          ) : null}

          <div className="workspace-scrollbar h-[calc(100vh-18rem)] min-h-[34rem] overflow-auto bg-zinc-50">
            <DataSurface
              activeKind={activeKind}
              documentPreview={selectedDocumentPreview}
              isGenerating={selectedRun?.status === "running" || status === "generating"}
              product={selectedProduct}
              selectedResource={selectedResource}
              tablePreview={selectedTablePreview}
            />
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
          visibleRows={visibleRows}
        />
      </div>
    </section>
  );
}

function WorkspaceSidebar({
  activeKind,
  collapsed,
  onToggleCollapse,
  products,
  selectedProductId,
  subscribedProductIds,
  resourceNames,
  selectedResource,
  onSelectProduct,
  onSelectResource,
}: {
  activeKind: Product["kind"];
  collapsed: boolean;
  onToggleCollapse: () => void;
  products: Product[];
  selectedProductId: string;
  subscribedProductIds: Set<string>;
  resourceNames: string[];
  selectedResource: string | null;
  onSelectProduct: (product: Product) => void;
  onSelectResource: (resourceName: string) => void;
}) {
  const ResourceIcon = activeKind === "document" ? FileJson : Table2;

  if (collapsed) {
    return (
      <aside className="bg-[#080b14] text-zinc-100">
        <div className="grid border-b border-white/10 px-2 py-3">
          <button
            aria-label="Expand workspace rail"
            className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 text-zinc-400 transition hover:border-cyan-300/30 hover:text-cyan-100"
            onClick={onToggleCollapse}
            title="Expand workspace rail"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-2">
          <div className="space-y-2">
            {products.map((product) => {
              const ProductIcon = productIcon(product.kind);
              const selected = selectedProductId === product.id;
              return (
                <button
                  key={product.id}
                  className={`relative grid h-11 w-11 place-items-center rounded-xl border transition ${
                    selected
                      ? "border-cyan-300/40 bg-cyan-300/15 text-cyan-100"
                      : "border-white/10 bg-white/[0.025] text-zinc-500 hover:border-white/20 hover:text-white"
                  }`}
                  onClick={() => onSelectProduct(product)}
                  title={product.name}
                >
                  <ProductIcon className="h-4 w-4" />
                  {subscribedProductIds.has(product.id) ? (
                    <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-emerald-300" />
                  ) : null}
                </button>
              );
            })}
          </div>

          <div className="workspace-scrollbar-dark max-h-[45vh] space-y-2 overflow-auto border-t border-white/10 pt-4">
            {resourceNames.map((resourceName) => (
              <button
                key={resourceName}
                className={`grid h-10 w-11 place-items-center rounded-lg transition ${
                  selectedResource === resourceName
                    ? "bg-cyan-300/15 text-cyan-100 ring-1 ring-cyan-300/25"
                    : "text-zinc-500 hover:bg-white/[0.05] hover:text-white"
                }`}
                onClick={() => onSelectResource(resourceName)}
                title={shortTableName(resourceName)}
              >
                <ResourceIcon className="h-4 w-4" />
              </button>
            ))}
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className="bg-[#080b14] text-zinc-100">
      <div className="border-b border-white/10 px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase text-zinc-500">Workspace</p>
            <p className="mt-1 text-sm font-semibold text-white">{kindLabel(activeKind)}</p>
          </div>
          <button
            aria-label="Collapse workspace rail"
            className="grid h-9 w-9 place-items-center rounded-lg border border-white/10 text-zinc-400 transition hover:border-cyan-300/30 hover:text-cyan-100"
            onClick={onToggleCollapse}
            title="Collapse workspace rail"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="space-y-5 p-3">
        <div>
          <div className="flex items-center justify-between px-1">
            <p className="text-xs font-semibold uppercase text-zinc-500">Products</p>
            <span className="text-xs text-zinc-600">{products.length}</span>
          </div>
          <div className="mt-3 space-y-2">
            {products.map((product) => {
              const selected = selectedProductId === product.id;
              const ProductIcon = productIcon(product.kind);
              return (
                <button
                  key={product.id}
                  className={`w-full rounded-lg border text-left transition ${
                    selected
                      ? "border-cyan-300/35 bg-cyan-300/10 px-3 py-3 text-white"
                      : "border-white/10 bg-white/[0.02] px-3 py-2 text-zinc-400 hover:border-white/20 hover:bg-white/[0.05] hover:text-white"
                  }`}
                  onClick={() => onSelectProduct(product)}
                >
                  <span className="flex items-start gap-3">
                    <span
                      className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg border ${
                        selected
                          ? "border-cyan-300/30 bg-cyan-300/10 text-cyan-100"
                          : "border-white/10 bg-white/[0.03] text-zinc-500"
                      }`}
                    >
                      <ProductIcon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-semibold">{product.name}</span>
                        {subscribedProductIds.has(product.id) ? (
                          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-300" />
                        ) : (
                          <span
                            className={`h-2 w-2 rounded-full ${
                              product.status === "active" ? "bg-emerald-300" : "bg-sky-300"
                            }`}
                          />
                        )}
                      </span>
                      <span className="mt-1 block truncate text-xs text-zinc-500">
                        {product.module}
                      </span>
                      {selected ? (
                        <span className="mt-2 inline-flex rounded-md bg-emerald-300/10 px-2 py-1 text-[0.68rem] font-semibold uppercase text-emerald-200">
                          {product.status}
                        </span>
                      ) : null}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between px-1">
            <p className="text-xs font-semibold uppercase text-zinc-600">
              {activeKind === "document" ? "Collections" : "Resources"}
            </p>
            <span className="text-xs text-zinc-600">{resourceNames.length}</span>
          </div>
          <div className="workspace-scrollbar-dark mt-3 max-h-[35vh] space-y-1.5 overflow-auto pr-1">
            {resourceNames.map((tableName) => (
              <button
                key={tableName}
                className={`flex h-10 w-full items-center gap-2 rounded-lg px-2.5 text-left text-sm transition ${
                  selectedResource === tableName
                    ? "bg-cyan-300/15 text-cyan-100 ring-1 ring-cyan-300/25"
                    : "text-zinc-400 hover:bg-white/[0.05] hover:text-white"
                }`}
                onClick={() => onSelectResource(tableName)}
              >
                <ResourceIcon className="h-4 w-4 shrink-0" />
                <span className="truncate">{shortTableName(tableName)}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

function WorkspaceOverview({
  artifacts,
  product,
  run,
  subscribed,
  visibleRows,
}: {
  artifacts: ArtifactList | null;
  product: Product | null;
  run: GenerationRun | null;
  subscribed: boolean;
  visibleRows: number;
}) {
  const resourceCount = product ? productResources(product).length : 0;
  const plannedRecords = product
    ? Object.values(product.default_row_counts).reduce((total, count) => total + count, 0)
    : 0;
  const progress = run ? progressPercent(run) : 0;
  const runState = runStateLabel(run);

  return (
    <section className="border-b border-zinc-200 bg-white">
      <div className="grid gap-4 px-5 py-4 2xl:grid-cols-[minmax(0,1fr)_auto] 2xl:items-center">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase ${
                product?.status === "active"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-sky-200 bg-sky-50 text-sky-700"
              }`}
            >
              <PackageCheck className="h-3.5 w-3.5" />
              {product?.status ?? "No product"}
            </span>
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase ${
                subscribed
                  ? "border-cyan-200 bg-cyan-50 text-cyan-700"
                  : "border-zinc-200 bg-zinc-50 text-zinc-500"
              }`}
            >
              {subscribed ? "Subscribed" : "Not subscribed"}
            </span>
          </div>

          <h1 className="mt-3 truncate text-2xl font-semibold text-zinc-950">
            {product?.name ?? "DataBoom workspace"}
          </h1>
          <p className="mt-1 max-w-3xl truncate text-sm text-zinc-500">
            {product?.description ??
              "Choose a product module, subscribe, generate a run, and inspect output artifacts."}
          </p>

          {run ? (
            <div className="mt-3">
              <div className="mb-2 flex items-center justify-between gap-3 text-xs font-semibold text-zinc-500">
                <span className="truncate">
                  Latest run · {run.run_id} · {runState}
                </span>
                <span>{progress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          ) : null}
        </div>

        <div className="grid gap-2 sm:grid-cols-4 2xl:w-[32rem]">
          <OverviewMetric
            icon={Database}
            label="Planned records"
            value={formatNumber(plannedRecords)}
          />
          <OverviewMetric
            icon={Layers3}
            label={product?.kind === "document" ? "Collections" : "Resources"}
            value={String(resourceCount)}
          />
          <OverviewMetric
            icon={BarChart3}
            label="Preview rows"
            value={String(visibleRows)}
          />
          <OverviewMetric
            icon={Download}
            label="Artifacts"
            value={String(artifacts?.files.length ?? 0)}
          />
        </div>
      </div>
    </section>
  );
}

function OverviewMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase text-zinc-500">{label}</p>
        <Icon className="h-4 w-4 text-cyan-700" />
      </div>
      <p className="mt-1 text-xl font-semibold text-zinc-950">{value}</p>
    </div>
  );
}

function WorkspaceToolbar({
  run,
  activeKind,
  selectedResource,
  artifacts,
  isRefreshing,
  onRefresh,
}: {
  run: GenerationRun | null;
  activeKind: Product["kind"];
  selectedResource: string | null;
  artifacts: ArtifactList | null;
  isRefreshing: boolean;
  onRefresh: () => void;
}) {
  const resource =
    run?.tables.find((item) => item.table_name === selectedResource) ??
    run?.collections.find((item) => item.collection_name === selectedResource);

  return (
    <header className="flex min-h-14 flex-col gap-3 border-b border-zinc-200 bg-zinc-50 px-5 py-2.5 lg:flex-row lg:items-center lg:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="truncate text-lg font-semibold text-zinc-950">
            {selectedResource ? shortTableName(selectedResource) : "Data workspace"}
          </h1>
          <span className="rounded-md bg-zinc-100 px-2 py-1 text-xs font-semibold text-zinc-500">
            {resource ? `${resource.row_count} records` : "No run"}
          </span>
        </div>
        <p className="mt-1 truncate text-xs text-zinc-500">
          {run ? run.run_id : "DataBoom Workspace"}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <ToolbarPill active icon={Table2} label={activeKind === "document" ? "Documents" : "Table"} />
        <ArtifactShortcut artifacts={artifacts} extension=".json" icon={FileJson} label="JSON" />
        <ArtifactShortcut artifacts={artifacts} extension=".ndjson" icon={FileText} label="NDJSON" />
        <ArtifactShortcut artifacts={artifacts} extension=".sql" icon={FileText} label="SQL" />
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
  icon: LucideIcon;
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
  icon: LucideIcon;
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

function DataSurface({
  activeKind,
  documentPreview,
  isGenerating,
  product,
  selectedResource,
  tablePreview,
}: {
  activeKind: Product["kind"];
  documentPreview: DocumentPreview | null;
  isGenerating: boolean;
  product: Product | null;
  selectedResource: string | null;
  tablePreview: TablePreview | null;
}) {
  if (activeKind === "document") {
    return (
      <DocumentList
        isGenerating={isGenerating}
        preview={documentPreview}
        selectedResource={selectedResource}
      />
    );
  }

  if (activeKind === "graph" || activeKind === "masking") {
    return <PlannedSurface product={product} />;
  }

  return (
    <DataTable
      isGenerating={isGenerating}
      preview={tablePreview}
      selectedResource={selectedResource}
    />
  );
}

function DataTable({
  isGenerating,
  preview,
  selectedResource,
}: {
  isGenerating: boolean;
  preview: TablePreview | null;
  selectedResource: string | null;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const rows = preview?.rows ?? [];
  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return rows;
    }
    return rows.filter((row) =>
      Object.values(row).some((value) => String(value).toLowerCase().includes(normalizedQuery)),
    );
  }, [query, rows]);
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const activePage = Math.min(page, pageCount);
  const startIndex = (activePage - 1) * pageSize;
  const visibleRows = filteredRows.slice(startIndex, startIndex + pageSize);

  useEffect(() => {
    setPage(1);
    setQuery("");
  }, [preview?.run_id, preview?.table_name]);

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);

  if (!preview) {
    return (
      <div className="grid h-full place-items-center px-6 text-center">
        <div>
          <Rows3 className="mx-auto h-10 w-10 text-zinc-300" />
          <p className="mt-4 text-lg font-semibold text-zinc-950">
            {selectedResource ? shortTableName(selectedResource) : "No table selected"}
          </p>
          <p className="mt-2 text-sm text-zinc-500">
            {isGenerating
              ? "Waiting for the first streamed rows from the generator."
              : "Generate a relational run to populate this grid."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-w-0 flex-col bg-zinc-50">
      <div className="flex flex-col gap-3 border-b border-zinc-200 bg-white px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-zinc-100 px-2.5 py-1 text-xs font-semibold text-zinc-500">
            {filteredRows.length} preview rows
          </span>
          <button className="rounded-md border border-zinc-200 px-2.5 py-1 text-xs font-semibold text-zinc-600 transition hover:border-cyan-400 hover:text-cyan-700">
            Columns
          </button>
        </div>
        <label className="flex h-9 min-w-0 items-center gap-2 rounded-md border border-zinc-200 bg-zinc-50 px-3 text-sm text-zinc-500 focus-within:border-cyan-500 lg:w-64">
          <Search className="h-4 w-4 shrink-0" />
          <input
            className="min-w-0 flex-1 bg-transparent text-sm text-zinc-800 outline-none placeholder:text-zinc-400"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search preview rows..."
            value={query}
          />
        </label>
      </div>

      <div className="workspace-scrollbar min-h-0 flex-1 overflow-auto bg-white">
        <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
          <thead className="sticky top-0 z-10 bg-zinc-50 shadow-[0_1px_0_rgba(228,228,231,1)]">
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
            {visibleRows.map((row, rowIndex) => {
              const rowNumber = startIndex + rowIndex + 1;
              const rowTone = rowNumber % 2 === 0 ? "bg-zinc-50" : "bg-white";
              return (
                <tr key={`${rowNumber}-${rowIndex}`} className={`${rowTone} hover:bg-cyan-50/80`}>
                  <td className="border-b border-r border-zinc-100 px-3 py-2 text-xs font-semibold text-zinc-400">
                    {rowNumber}
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
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-zinc-200 bg-white px-4 py-3 text-xs font-semibold text-zinc-500 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <span>Rows per page</span>
          <select
            className="h-8 rounded-md border border-zinc-200 bg-zinc-50 px-2 text-xs font-semibold text-zinc-700 outline-none focus:border-cyan-500"
            onChange={(event) => {
              setPageSize(Number(event.target.value));
              setPage(1);
            }}
            value={pageSize}
          >
            {[10, 20].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            className="h-8 rounded-md border border-zinc-200 px-2.5 text-zinc-600 transition hover:border-cyan-400 hover:text-cyan-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={activePage <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            Prev
          </button>
          {paginationItems(pageCount, activePage).map((item, index) =>
            item === "gap" ? (
              <span key={`gap-${index}`} className="px-1 text-zinc-400">
                ...
              </span>
            ) : (
              <button
                key={item}
                className={`grid h-8 min-w-8 place-items-center rounded-md border px-2 transition ${
                  item === activePage
                    ? "border-cyan-500 bg-cyan-50 text-cyan-700"
                    : "border-zinc-200 text-zinc-600 hover:border-cyan-400 hover:text-cyan-700"
                }`}
                onClick={() => setPage(item)}
              >
                {item}
              </button>
            ),
          )}
          <button
            className="h-8 rounded-md border border-zinc-200 px-2.5 text-zinc-600 transition hover:border-cyan-400 hover:text-cyan-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={activePage >= pageCount}
            onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

function DocumentList({
  isGenerating,
  preview,
  selectedResource,
}: {
  isGenerating: boolean;
  preview: DocumentPreview | null;
  selectedResource: string | null;
}) {
  if (!preview) {
    return (
      <div className="grid h-full place-items-center px-6 text-center">
        <div>
          <Rows3 className="mx-auto h-10 w-10 text-zinc-300" />
          <p className="mt-4 text-lg font-semibold text-zinc-950">
            {selectedResource ?? "No collection selected"}
          </p>
          <p className="mt-2 text-sm text-zinc-500">
            {isGenerating
              ? "Waiting for the first streamed documents from the generator."
              : "Generate a Docu-Boom run to populate this document preview."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-4 p-5 xl:grid-cols-2">
      {preview.documents.map((document, index) => (
        <article key={index} className="rounded-md border border-zinc-200 bg-zinc-50">
          <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-2">
            <p className="text-xs font-semibold uppercase text-zinc-400">Document {index + 1}</p>
            <p className="text-xs font-semibold text-zinc-500">{preview.collection_name}</p>
          </div>
          <pre className="workspace-scrollbar max-h-96 overflow-auto p-4 text-xs leading-5 text-zinc-800">
            {JSON.stringify(document, null, 2)}
          </pre>
        </article>
      ))}
    </div>
  );
}

function PlannedSurface({ product }: { product: Product | null }) {
  return (
    <div className="grid h-full place-items-center px-6 text-center">
      <div className="max-w-lg">
        <Sparkles className="mx-auto h-10 w-10 text-zinc-300" />
        <p className="mt-4 text-lg font-semibold text-zinc-950">
          {product?.name ?? "Planned product"}
        </p>
        <p className="mt-2 text-sm leading-6 text-zinc-500">
          This product is visible in the catalog but its runtime workspace is planned for a later
          phase.
        </p>
      </div>
    </div>
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
  const busy = status === "generating" || status === "subscribing" || run?.status === "running";
  const runState = runStateLabel(run);
  const runStateClass =
    run?.status === "running"
      ? "border-cyan-200 bg-cyan-50 text-cyan-700"
      : run?.validation?.passed
        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
        : "border-zinc-200 bg-zinc-50 text-zinc-500";

  return (
    <aside className="flex min-h-full flex-col bg-zinc-50 text-zinc-950">
      <div className="border-b border-zinc-200 bg-white px-4 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase text-zinc-400">Run builder</p>
            <h2 className="mt-1 truncate text-lg font-semibold text-zinc-950">
              {selectedProduct?.name ?? "Select a product"}
            </h2>
          </div>
          <span
            className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${runStateClass}`}
          >
            {run?.status === "running" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : run?.validation?.passed ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <CircleAlert className="h-3.5 w-3.5" />
            )}
            {runState}
          </span>
        </div>

        <GenerationPulse active={busy} />

        <div className="mt-4 rounded-xl border border-zinc-200 bg-zinc-50 p-3">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="text-xs font-semibold uppercase text-zinc-500">
              Generation brief
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-700">
              <Sparkles className="h-3.5 w-3.5" />
              deterministic seed
            </span>
          </div>
          <textarea
            className="h-20 w-full resize-none rounded-lg border border-zinc-200 bg-white p-3 text-sm leading-6 text-zinc-800 outline-none transition focus:border-cyan-500"
            onChange={(event) => onPromptChange(event.target.value)}
            value={prompt}
          />
          <div className="mt-3 flex items-center justify-between gap-3">
            <span className="truncate text-xs font-semibold text-zinc-500">
              {selectedProduct?.kind ?? "No product"} · {visibleRows} preview rows
            </span>
            {subscribed ? (
              <button
                className="inline-flex h-10 items-center gap-2 rounded-lg bg-zinc-950 px-4 text-sm font-semibold text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={busy || !selectedProduct || selectedProduct.status !== "active"}
                onClick={onGenerate}
              >
                {status === "generating" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                {status === "generating" ? "Generating" : "Generate"}
              </button>
            ) : (
              <button
                className="inline-flex h-10 items-center gap-2 rounded-lg bg-cyan-700 px-4 text-sm font-semibold text-white transition hover:bg-cyan-600 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={busy || !selectedProduct || selectedProduct.status !== "active"}
                onClick={onSubscribe}
              >
                {status === "subscribing" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {selectedProduct?.status === "planned" ? "Planned" : "Subscribe"}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="workspace-scrollbar min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
        <details className="rounded-xl border border-zinc-200 bg-white p-3">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-zinc-950">
            Generation steps
            <ChevronDown className="h-4 w-4 text-zinc-400" />
          </summary>
          <div className="mt-3 space-y-2">
            {steps.map((step) => (
              <div key={step.label} className="rounded-lg border border-zinc-100 bg-zinc-50 p-3">
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
        </details>

        <RunSummary run={run} visibleRows={visibleRows} />
        <InsightPanel insight={insight} />
        <ArtifactListPanel artifacts={artifacts} />
      </div>
    </aside>
  );
}

function GenerationPulse({ active }: { active: boolean }) {
  return (
    <div className="mt-4 rounded-xl border border-cyan-200 bg-cyan-50 px-3 py-2.5">
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-900">
          {active ? (
            <Loader2 className="h-4 w-4 animate-spin text-cyan-700" />
          ) : (
            <Clock3 className="h-4 w-4 text-cyan-700" />
          )}
          {active ? "Generation in progress" : "Generator ready"}
        </span>
        <span className="text-xs font-semibold uppercase text-cyan-700">
          async engine
        </span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white">
        <div
          className={`h-full rounded-full ${
            active
              ? "w-2/3 animate-pulse bg-cyan-500"
              : "w-full bg-gradient-to-r from-emerald-500 to-cyan-500"
          }`}
        />
      </div>
    </div>
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

  const progress = progressPercent(run);

  return (
    <section className="rounded-md border border-zinc-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-zinc-950">Run summary</h3>
        <span className="rounded-md bg-zinc-100 px-2 py-1 text-xs font-semibold text-zinc-500">
          {run.status}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Metric label="Rows" value={String(run.total_rows)} />
        <Metric label="Generated" value={`${run.generated_rows}/${run.total_rows}`} />
        <Metric
          label={run.kind === "document" ? "Collections" : "Tables"}
          value={String(run.table_count)}
        />
        <Metric label="Preview" value={String(visibleRows)} />
        <Metric
          label={run.status === "running" ? "Expected" : "Duration"}
          value={
            run.status === "running"
              ? formatDuration(run.expected_seconds)
              : formatDuration(totalRunSeconds(run))
          }
        />
        <Metric label="Rate" value={formatRate(run.rows_per_second)} />
      </div>
      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-xs font-semibold text-zinc-500">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        {run.status === "running" ? (
          <p className="mt-2 truncate text-xs font-semibold text-zinc-500">
            {run.current_resource
              ? `${formatOperationName(run.current_operation ?? "generate")} · ${shortTableName(
                  run.current_resource,
                )}`
              : formatOperationName(run.current_operation ?? "starting")}
            {run.remaining_seconds !== null
              ? ` · ${formatDuration(run.remaining_seconds)} remaining`
              : ""}
          </p>
        ) : null}
      </div>
      <div className="mt-4 space-y-2">
        {runResourcesWithCounts(run).map((resource) => (
          <div key={resource.name} className="flex items-center justify-between gap-3 text-sm">
            <span className="truncate text-zinc-600">{shortTableName(resource.name)}</span>
            <span className="font-semibold text-zinc-950">{resource.rowCount}</span>
          </div>
        ))}
      </div>
      {run.operation_timings.length ? (
        <div className="mt-4 border-t border-zinc-100 pt-4">
          <p className="text-xs font-semibold uppercase text-zinc-400">Operation timings</p>
          <div className="mt-2 space-y-2">
            {run.operation_timings.map((timing) => (
              <div
                key={timing.operation}
                className="flex items-center justify-between gap-3 text-xs"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${statusDotClass(timing.status)}`} />
                  <span className="truncate font-semibold text-zinc-600">
                    {formatOperationName(timing.operation)}
                  </span>
                </span>
                <span className="shrink-0 font-semibold text-zinc-950">
                  {formatDuration(timing.elapsed_seconds)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
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
          <h3 className="text-sm font-semibold text-zinc-950">Data insight</h3>
        </div>
        <p className="mt-2 text-sm leading-6 text-zinc-500">No distribution available.</p>
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

async function loadTablePreviewSafe(runId: string, tableName: string) {
  try {
    return await getTablePreview(runId, tableName, 20);
  } catch {
    return null;
  }
}

async function loadDocumentPreviewSafe(runId: string, collectionName: string) {
  try {
    return await getDocumentPreview(runId, collectionName, 20);
  } catch {
    return null;
  }
}

function upsertRun(runs: GenerationRun[], run: GenerationRun) {
  const exists = runs.some((item) => item.run_id === run.run_id);
  if (!exists) {
    return [...runs, run];
  }
  return runs.map((item) => (item.run_id === run.run_id ? run : item));
}

function runAgentStatus(run: GenerationRun): AgentStatus {
  if (run.status === "running" || run.status === "pending") {
    return "generating";
  }
  if (run.status === "failed") {
    return "error";
  }
  return "complete";
}

function runStateLabel(run: GenerationRun | null) {
  if (!run) {
    return "Waiting";
  }
  if (run.status === "running") {
    return "Running";
  }
  if (run.status === "failed") {
    return "Failed";
  }
  if (run.validation?.passed) {
    return "Validated";
  }
  return "Completed";
}

function progressPercent(run: GenerationRun) {
  if (run.status === "completed") {
    return 100;
  }
  return Math.min(100, Math.max(0, Math.round(run.progress_percent ?? 0)));
}

function totalRunSeconds(run: GenerationRun) {
  return (
    run.operation_timings.find((timing) => timing.operation === "total_run")?.elapsed_seconds ??
    run.operation_timings.at(-1)?.elapsed_seconds ??
    null
  );
}

function formatDuration(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined) {
    return "Pending";
  }
  if (seconds < 1) {
    return `${Math.max(0.01, seconds).toFixed(2)}s`;
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

function formatRate(rowsPerSecond: number | null | undefined) {
  if (!rowsPerSecond) {
    return "Pending";
  }
  if (rowsPerSecond < 1) {
    return `${rowsPerSecond.toFixed(2)}/s`;
  }
  return `${Math.round(rowsPerSecond).toLocaleString()}/s`;
}

function formatNumber(value: number) {
  return value.toLocaleString();
}

function formatOperationName(operation: string) {
  return operation
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusDotClass(status: string) {
  if (status === "completed") {
    return "bg-emerald-500";
  }
  if (status === "running") {
    return "bg-cyan-500";
  }
  if (status === "failed") {
    return "bg-red-500";
  }
  return "bg-zinc-300";
}

function delay(milliseconds: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function buildAgentSteps(
  status: AgentStatus,
  run: GenerationRun | null,
  product: Product | null,
): AgentStep[] {
  const done = status === "complete" || run?.status === "completed";
  const active = status === "generating";
  const resourceCount = product ? productResources(product).length : 0;
  const resourceLabel = product?.kind === "document" ? "collections" : "resources";
  return [
    {
      label: product?.kind === "document" ? "Read document spec" : "Read data shape",
      detail: product ? `${resourceCount} ${resourceLabel} in ${product.name}` : "Waiting for dataset",
      state: done ? "done" : active ? "active" : "waiting",
    },
    {
      label: "Resolve identifiers",
      detail:
        product?.kind === "document"
          ? "Object IDs, nested fields, arrays, and references"
          : "Primary keys, foreign keys, and generation order",
      state: done ? "done" : active ? "active" : "waiting",
    },
    {
      label: product?.kind === "document" ? "Generate documents" : "Generate rows",
      detail: run ? `${run.total_rows} records written` : "Local artifact stream",
      state: done ? "done" : active ? "active" : "waiting",
    },
    {
      label: "Validate and export",
      detail: run?.validation?.passed ? "Validation passed" : "Awaiting validation report",
      state: done && run?.validation?.passed ? "done" : active ? "active" : "waiting",
    },
  ];
}

function buildInsight(
  tablePreview: TablePreview | null,
  documentPreview: DocumentPreview | null,
): Insight | null {
  if (documentPreview) {
    return buildDocumentInsight(documentPreview);
  }
  if (!tablePreview || tablePreview.rows.length === 0) {
    return null;
  }

  const preferredColumn =
    ["status", "gender", "age", "payment_method", "payment_method_id"].find((column) =>
      tablePreview.columns.includes(column),
    ) ??
    tablePreview.columns.find(
      (column) => new Set(tablePreview.rows.map((row) => row[column])).size <= 6,
    );

  if (!preferredColumn) {
    return null;
  }

  const counts = new Map<string, number>();
  for (const row of tablePreview.rows) {
    const label = bucketValue(preferredColumn, row[preferredColumn] ?? "empty");
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }

  const total = tablePreview.rows.length;
  return {
    title: `${shortTableName(tablePreview.table_name)} by ${preferredColumn}`,
    values: Array.from(counts.entries()).map(([label, count]) => ({
      label,
      count,
      percent: Math.max(4, Math.round((count / total) * 100)),
    })),
  };
}

function buildDocumentInsight(preview: DocumentPreview): Insight | null {
  if (preview.documents.length === 0) {
    return null;
  }

  const counts = new Map<string, number>();
  for (const document of preview.documents) {
    const value = document.status ?? document.event_name ?? document._id ?? "document";
    const label = String(value);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }

  const total = preview.documents.length;
  return {
    title: `${preview.collection_name} distribution`,
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
  if (run.kind !== product.kind) {
    return false;
  }
  const runResourceNames = new Set(runResources(run).map(shortTableName));
  return productResources(product).some((resource) => runResourceNames.has(resource));
}

function runResources(run: GenerationRun) {
  if (run.kind === "document") {
    return run.collections.map((collection) => collection.collection_name);
  }
  return run.tables.map((table) => table.table_name);
}

function runResourcesWithCounts(run: GenerationRun) {
  if (run.kind === "document") {
    return run.collections.map((collection) => ({
      name: collection.collection_name,
      rowCount: collection.row_count,
    }));
  }
  return run.tables.map((table) => ({ name: table.table_name, rowCount: table.row_count }));
}

function productResources(product: Product | null) {
  if (!product) {
    return [];
  }
  if (product.kind === "document") {
    return product.collections;
  }
  if (product.kind === "relational") {
    return product.tables;
  }
  return product.use_cases;
}

function paginationItems(pageCount: number, activePage: number) {
  if (pageCount <= 5) {
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  }

  const pages = new Set([1, pageCount, activePage - 1, activePage, activePage + 1]);
  return Array.from(pages)
    .filter((page) => page >= 1 && page <= pageCount)
    .sort((left, right) => left - right)
    .reduce<(number | "gap")[]>((items, page) => {
      const previous = items.at(-1);
      if (typeof previous === "number" && page - previous > 1) {
        items.push("gap");
      }
      items.push(page);
      return items;
    }, []);
}

function productIcon(kind: Product["kind"]) {
  if (kind === "document") {
    return FileJson;
  }
  if (kind === "graph") {
    return Layers3;
  }
  if (kind === "masking") {
    return PackageCheck;
  }
  return HardDrive;
}

function kindLabel(kind: Product["kind"]) {
  if (kind === "document") {
    return "NoSQL documents";
  }
  if (kind === "graph") {
    return "Graph data";
  }
  if (kind === "masking") {
    return "Masking";
  }
  return "Relational";
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
