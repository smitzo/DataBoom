"use client";

import {
  ArrowLeft,
  BarChart3,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Clock3,
  Database,
  Download,
  Eye,
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
  Rows3,
  Search,
  Send,
  Sparkles,
  Table2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type {
  ArtifactList,
  DocumentPreview,
  GenerationRun,
  Product,
  Subscription,
  TablePreview,
  WorkspaceSource,
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
  getWorkspaceSources,
  refreshWorkspaceSource,
  subscribeToProduct,
} from "@/lib/api";
import type { Session } from "@/lib/session";

type PreviewMap = Record<string, TablePreview>;
type DocumentPreviewMap = Record<string, DocumentPreview>;
type AgentStatus = "idle" | "subscribing" | "generating" | "complete" | "error";
type WorkspaceMode = "catalog" | "product";
type ViewFormat = "table" | "csv" | "sql" | "json" | "ndjson" | "graph" | "masked";

type FormatOption = {
  id: ViewFormat;
  label: string;
  description: string;
  extension?: string;
  icon: LucideIcon;
};

export function DataWorkspace({ session }: { session: Session }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [workspaceSources, setWorkspaceSources] = useState<WorkspaceSource[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactList | null>(null);
  const [previews, setPreviews] = useState<PreviewMap>({});
  const [documentPreviews, setDocumentPreviews] = useState<DocumentPreviewMap>({});
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [selectedConnectionId, setSelectedConnectionId] = useState<string>("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedResource, setSelectedResource] = useState<string | null>(null);
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("catalog");
  const [viewFormat, setViewFormat] = useState<ViewFormat>("table");
  const [downloadFormats, setDownloadFormats] = useState<ViewFormat[]>(["csv"]);
  const [prompt, setPrompt] = useState("Generate realistic data for the selected product");
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [sourceWarning, setSourceWarning] = useState<string | null>(null);
  const [sourceRefreshMessage, setSourceRefreshMessage] = useState<string | null>(null);
  const [sourceDatabaseUrl, setSourceDatabaseUrl] = useState("");
  const [sourceSchemaNames, setSourceSchemaNames] = useState("public");
  const [isRefreshingSource, setIsRefreshingSource] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
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
  const connectionOptions = useMemo(
    () => workspaceConnectionsForProduct(selectedProduct, workspaceSources),
    [selectedProduct, workspaceSources],
  );
  const selectedConnection =
    connectionOptions.find((connection) => connection.id === selectedConnectionId) ??
    connectionOptions[0] ??
    null;
  const resourceNames = selectedConnection
    ? connectionResources(selectedConnection, activeKind)
    : productResources(selectedProduct);
  const visibleRows = selectedTablePreview?.rows.length ?? selectedDocumentPreview?.documents.length ?? 0;

  useEffect(() => {
    if (!selectedProduct || connectionOptions.length === 0) {
      return;
    }
    if (!connectionOptions.some((connection) => connection.id === selectedConnectionId)) {
      const nextConnection = connectionOptions[0];
      setSelectedConnectionId(nextConnection.id);
      setSelectedResource(connectionResources(nextConnection, selectedProduct.kind)[0] ?? null);
    }
  }, [connectionOptions, selectedConnectionId, selectedProduct]);

  useEffect(() => {
    const nextViewOptions = viewOptions(activeKind);
    const nextDownloadOptions = downloadOptions(activeKind);
    setViewFormat((current) =>
      nextViewOptions.some((option) => option.id === current)
        ? current
        : nextViewOptions[0]?.id ?? "table",
    );
    setDownloadFormats((current) => {
      const allowedIds = new Set(nextDownloadOptions.map((option) => option.id));
      const filtered = current.filter((format) => allowedIds.has(format));
      return filtered.length ? filtered : nextDownloadOptions.slice(0, 1).map((option) => option.id);
    });
  }, [activeKind, selectedProductId]);

  const agentSteps = useMemo(
    () => buildAgentSteps(status, selectedRun, selectedProduct),
    [selectedProduct, selectedRun, status],
  );
  const insight = useMemo(
    () => buildInsight(selectedTablePreview, selectedDocumentPreview),
    [selectedDocumentPreview, selectedTablePreview],
  );
  const workspaceGridClass = isWorkspaceRailCollapsed
    ? "flex min-h-[calc(100vh-5.5rem)] flex-col xl:grid xl:grid-cols-[9.5rem_minmax(0,1fr)_21rem]"
    : "flex min-h-[calc(100vh-5.5rem)] flex-col xl:grid xl:grid-cols-[15rem_minmax(0,1fr)_21rem]";

  async function loadWorkspace() {
    setIsLoading(true);
    setError(null);
    setSourceWarning(null);
    try {
      const [nextProducts, nextSubscriptions, nextRuns] = await Promise.all([
        getProducts(),
        getSubscriptions(session.token),
        getRuns(),
      ]);
      let nextSources: WorkspaceSource[];
      try {
        nextSources = await getWorkspaceSources();
      } catch {
        nextSources = fallbackWorkspaceSources(nextProducts);
        setSourceWarning(
          "Using local demo workspaces. Restart the backend to load workspace sources from the API.",
        );
      }
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
      const firstConnection = workspaceConnectionsForProduct(firstProduct, nextSources)[0] ?? null;

      setProducts(nextProducts);
      setWorkspaceSources(nextSources);
      setSubscriptions(nextSubscriptions);
      setRuns(nextRuns);
      setSelectedProductId(firstProductId);
      setSelectedConnectionId(firstConnection?.id ?? "");
      setSelectedRunId(firstRun?.run_id ?? null);
      setSelectedResource(
        firstConnection
          ? connectionResources(firstConnection, firstProduct?.kind ?? "relational")[0] ?? null
          : firstRun
            ? runResources(firstRun)[0] ?? null
            : productResources(firstProduct)[0] ?? null,
      );
      setStatus(firstRun ? runAgentStatus(firstRun) : "idle");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to load workspace");
      setStatus("error");
    } finally {
      setIsLoading(false);
    }
  }

  async function chooseProduct(product: Product) {
    setSelectedProductId(product.id);
    setSourceRefreshMessage(null);
    const matchingRun = runs.slice().reverse().find((run) => runMatchesProduct(run, product));
    const nextConnection = workspaceConnectionsForProduct(product, workspaceSources)[0] ?? null;
    setSelectedRunId(matchingRun?.run_id ?? null);
    setSelectedConnectionId(nextConnection?.id ?? "");
    setSelectedResource(
      nextConnection
        ? connectionResources(nextConnection, product.kind)[0] ?? null
        : matchingRun
          ? runResources(matchingRun)[0] ?? null
          : productResources(product)[0] ?? null,
    );
    setStatus(matchingRun ? runAgentStatus(matchingRun) : "idle");
    setWorkspaceMode("product");
  }

  function chooseConnection(connectionId: string) {
    const nextConnection = connectionOptions.find((connection) => connection.id === connectionId);
    setSelectedConnectionId(connectionId);
    setSourceRefreshMessage(null);
    setSelectedResource(
      nextConnection ? connectionResources(nextConnection, activeKind)[0] ?? null : null,
    );
  }

  async function refreshSelectedSource() {
    if (!selectedConnection) {
      return;
    }
    if (activeKind !== "relational") {
      setSourceRefreshMessage("Schema refresh is currently available for PostgreSQL sources.");
      return;
    }
    if (!sourceDatabaseUrl.trim()) {
      setSourceRefreshMessage("Enter a PostgreSQL connection URL before refreshing.");
      return;
    }

    setIsRefreshingSource(true);
    setSourceRefreshMessage(null);
    setError(null);
    try {
      const schemaNames = sourceSchemaNames
        .split(",")
        .map((schemaName) => schemaName.trim())
        .filter(Boolean);
      const refreshed = await refreshWorkspaceSource(session.token, selectedConnection.id, {
        database_url: sourceDatabaseUrl.trim(),
        schema_names: schemaNames.length ? schemaNames : ["public"],
      });
      setWorkspaceSources((current) => [
        ...current.filter((source) => source.id !== refreshed.id),
        refreshed,
      ]);
      setSelectedConnectionId(refreshed.id);
      setSelectedResource(connectionResources(refreshed, refreshed.kind)[0] ?? null);
      setSourceWarning(null);
      setSourceRefreshMessage(`Loaded ${refreshed.resources.length} tables from ${refreshed.name}.`);
    } catch (caughtError) {
      setSourceRefreshMessage(
        caughtError instanceof Error ? caughtError.message : "Unable to refresh source",
      );
    } finally {
      setIsRefreshingSource(false);
    }
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
      const sourceId =
        selectedConnection && !selectedConnection.id.endsWith("-local-demo")
          ? selectedConnection.id
          : undefined;
      const run = await createAsyncProductRun(session.token, selectedProduct.id, {
        row_counts: selectedConnection
          ? Object.fromEntries(
              selectedConnection.resources.map((resource) => [
                resource.name,
                Math.min(resource.estimated_rows, 10_000),
              ]),
            )
          : selectedProduct.default_row_counts,
        seed: `${selectedProduct.id}-workspace`,
        output_formats: downloadOptions(activeKind).map((option) => option.id),
        source_id: sourceId,
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

  if (workspaceMode === "catalog") {
    return (
      <ProductWorkspacePicker
        error={error}
        products={products}
        sourceWarning={sourceWarning}
        selectedProductId={selectedProductId}
        subscribedProductIds={subscribedProductIds}
        onSelectProduct={chooseProduct}
      />
    );
  }

  return (
    <section className="min-h-[calc(100vh-5.5rem)] overflow-hidden rounded-2xl border border-white/10 bg-zinc-950 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
      <div className={workspaceGridClass}>
        <WorkspaceSidebar
          activeKind={activeKind}
          collapsed={isWorkspaceRailCollapsed}
          connectionOptions={connectionOptions}
          onToggleCollapse={() => setIsWorkspaceRailCollapsed((current) => !current)}
          product={selectedProduct}
          resourceNames={resourceNames}
          selectedConnection={selectedConnection}
          selectedConnectionId={selectedConnectionId}
          selectedResource={selectedResource}
          sourceDatabaseUrl={sourceDatabaseUrl}
          sourceRefreshMessage={sourceRefreshMessage}
          sourceSchemaNames={sourceSchemaNames}
          onBackToProducts={() => setWorkspaceMode("catalog")}
          onRefreshSource={refreshSelectedSource}
          onSelectConnection={chooseConnection}
          onSelectResource={setSelectedResource}
          onSourceDatabaseUrlChange={setSourceDatabaseUrl}
          onSourceSchemaNamesChange={setSourceSchemaNames}
          isRefreshingSource={isRefreshingSource}
        />

        <main className="min-w-0 border-y border-white/10 bg-zinc-100 text-zinc-950 xl:border-x xl:border-y-0">
          <WorkspaceOverview
            connection={selectedConnection}
            product={selectedProduct}
            run={selectedRun}
            visibleRows={visibleRows}
          />
          <WorkspaceToolbar
            run={selectedRun}
            activeKind={activeKind}
            selectedResource={selectedResource}
            artifacts={artifacts}
            downloadFormats={downloadFormats}
            onDownloadFormatsChange={setDownloadFormats}
            onViewFormatChange={setViewFormat}
            product={selectedProduct}
            viewFormat={viewFormat}
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
              viewFormat={viewFormat}
            />
          </div>
        </main>

        <AgentPanel
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

function ProductWorkspacePicker({
  error,
  products,
  sourceWarning,
  selectedProductId,
  subscribedProductIds,
  onSelectProduct,
}: {
  error: string | null;
  products: Product[];
  sourceWarning: string | null;
  selectedProductId: string;
  subscribedProductIds: Set<string>;
  onSelectProduct: (product: Product) => void;
}) {
  return (
    <section className="min-h-[calc(100vh-5.5rem)] rounded-2xl border border-white/10 bg-[#070b16] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
      <div className="grid min-h-[calc(100vh-8rem)] gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(34rem,1.35fr)] xl:items-stretch">
        <div className="flex flex-col justify-between rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-200">
              Product workspaces
            </p>
            <h1 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight text-white lg:text-5xl">
              Pick the data surface before you run the engine.
            </h1>
            <p className="mt-5 max-w-xl text-sm leading-6 text-zinc-400">
              Each workspace opens with only the controls, previews, and artifacts that match that
              product. Relational data stays table-first. Document data stays JSON-first.
            </p>
          </div>

          <div className="mt-10 grid gap-3 sm:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
            {[
              ["Table-Boom", "Tables, keys, CSV and SQL"],
              ["Docu-Boom", "Documents, JSON and NDJSON"],
              ["Focused", "One product workspace at a time"],
            ].map(([label, detail]) => (
              <div key={label} className="rounded-xl border border-white/10 bg-black/20 p-4">
                <p className="text-sm font-semibold text-white">{label}</p>
                <p className="mt-2 text-xs leading-5 text-zinc-500">{detail}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {sourceWarning ? (
            <div className="rounded-2xl border border-amber-300/25 bg-amber-300/10 p-5 text-sm leading-6 text-amber-100 sm:col-span-2">
              {sourceWarning}
            </div>
          ) : null}
          {products.length === 0 ? (
            <div className="rounded-2xl border border-red-300/25 bg-red-300/10 p-6 sm:col-span-2">
              <p className="text-lg font-semibold text-red-100">Product catalog did not load.</p>
              <p className="mt-3 text-sm leading-6 text-red-100/75">
                {error ?? "Start or restart the backend API, then refresh this dashboard."}
              </p>
            </div>
          ) : null}
          {products.map((product) => {
            const Icon = productIcon(product.kind);
            const subscribed = subscribedProductIds.has(product.id);
            const selected = selectedProductId === product.id;
            const resourceCount = productResources(product).length;
            return (
              <button
                key={product.id}
                className={`group flex min-h-64 flex-col justify-between rounded-2xl border p-5 text-left transition ${
                  selected
                    ? "border-cyan-300/45 bg-cyan-300/10 shadow-[0_0_44px_rgba(34,211,238,0.12)]"
                    : "border-white/10 bg-white/[0.035] hover:border-cyan-300/30 hover:bg-cyan-300/[0.055]"
                }`}
                onClick={() => onSelectProduct(product)}
              >
                <span>
                  <span className="flex items-start justify-between gap-4">
                    <span className="grid h-12 w-12 place-items-center rounded-2xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-100">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span
                      className={`rounded-full border px-3 py-1 text-[0.68rem] font-semibold uppercase ${
                        product.status === "active"
                          ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-200"
                          : "border-sky-300/25 bg-sky-300/10 text-sky-200"
                      }`}
                    >
                      {product.status}
                    </span>
                  </span>
                  <span className="mt-5 block text-2xl font-semibold text-white">
                    {product.name}
                  </span>
                  <span className="mt-2 block text-sm text-zinc-500">{product.module}</span>
                  <span className="mt-4 block text-sm leading-6 text-zinc-400">
                    {product.description}
                  </span>
                </span>

                <span className="mt-6 flex items-center justify-between gap-3 border-t border-white/10 pt-4">
                  <span className="text-xs font-semibold uppercase text-zinc-500">
                    {resourceCount} {product.kind === "document" ? "collections" : "resources"}
                  </span>
                  <span className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-100">
                    {subscribed ? "Open workspace" : "Preview workspace"}
                    <PanelLeftOpen className="h-4 w-4 transition group-hover:translate-x-0.5" />
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function WorkspaceSidebar({
  activeKind,
  collapsed,
  connectionOptions,
  isRefreshingSource,
  onToggleCollapse,
  product,
  resourceNames,
  selectedConnection,
  selectedConnectionId,
  selectedResource,
  sourceDatabaseUrl,
  sourceRefreshMessage,
  sourceSchemaNames,
  onBackToProducts,
  onRefreshSource,
  onSelectConnection,
  onSelectResource,
  onSourceDatabaseUrlChange,
  onSourceSchemaNamesChange,
}: {
  activeKind: Product["kind"];
  collapsed: boolean;
  connectionOptions: WorkspaceSource[];
  isRefreshingSource: boolean;
  onToggleCollapse: () => void;
  product: Product | null;
  resourceNames: string[];
  selectedConnection: WorkspaceSource | null;
  selectedConnectionId: string;
  selectedResource: string | null;
  sourceDatabaseUrl: string;
  sourceRefreshMessage: string | null;
  sourceSchemaNames: string;
  onBackToProducts: () => void;
  onRefreshSource: () => void;
  onSelectConnection: (connectionId: string) => void;
  onSelectResource: (resourceName: string) => void;
  onSourceDatabaseUrlChange: (value: string) => void;
  onSourceSchemaNamesChange: (value: string) => void;
}) {
  const ResourceIcon = activeKind === "document" ? FileJson : Table2;
  const ProductIcon = product ? productIcon(product.kind) : Database;
  const resourceLabel = activeKind === "document" ? "Collections" : "Tables";

  if (collapsed) {
    return (
      <aside className="bg-[#080b14] text-zinc-100">
        <div className="grid gap-2 border-b border-white/10 px-2 py-3">
          <button
            aria-label="Expand workspace rail"
            className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 text-zinc-400 transition hover:border-cyan-300/30 hover:text-cyan-100"
            onClick={onToggleCollapse}
            title="Expand workspace rail"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>
          <button
            className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 text-zinc-400 transition hover:border-white/20 hover:text-white"
            onClick={onBackToProducts}
            title="Back to products"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-2">
          <div className="rounded-xl border border-cyan-300/25 bg-cyan-300/10 p-2 text-cyan-100">
            <div className="flex items-center gap-2" title={product?.name ?? "Product"}>
              <ProductIcon className="h-4 w-4 shrink-0" />
              <span className="truncate text-xs font-semibold">{product?.name ?? "Product"}</span>
            </div>
            <p className="mt-2 truncate text-[0.68rem] font-semibold uppercase text-cyan-200/70">
              {selectedConnection?.name ?? "No database"}
            </p>
          </div>

          <div className="workspace-scrollbar-dark max-h-[45vh] space-y-2 overflow-auto border-t border-white/10 pt-4">
            {resourceNames.map((resourceName) => (
              <button
                key={resourceName}
                className={`flex h-10 w-full items-center gap-2 rounded-lg px-2 text-left transition ${
                  selectedResource === resourceName
                    ? "bg-cyan-300/15 text-cyan-100 ring-1 ring-cyan-300/25"
                    : "text-zinc-500 hover:bg-white/[0.05] hover:text-white"
                }`}
                onClick={() => onSelectResource(resourceName)}
                title={shortTableName(resourceName)}
              >
                <ResourceIcon className="h-4 w-4" />
                <span className="max-w-20 truncate text-[0.68rem] font-semibold">
                  {shortTableName(resourceName)}
                </span>
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
            <p className="mt-1 text-sm font-semibold text-white">{product?.name ?? kindLabel(activeKind)}</p>
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
        <details className="group rounded-xl border border-white/10 bg-white/[0.025] p-3" open>
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
            <span className="flex min-w-0 items-center gap-3">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-cyan-300/25 bg-cyan-300/10 text-cyan-100">
                <ProductIcon className="h-4 w-4" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-white">
                  {product?.name ?? "Product"}
                </span>
                <span className="mt-1 block truncate text-xs text-zinc-500">
                  {product?.module ?? kindLabel(activeKind)}
                </span>
              </span>
            </span>
            <ChevronDown className="h-4 w-4 shrink-0 text-zinc-500 transition group-open:rotate-180" />
          </summary>

          <div className="mt-4 space-y-3">
            <label className="block">
              <span className="text-[0.68rem] font-semibold uppercase text-zinc-600">
                Connected database
              </span>
              <select
                className="mt-2 h-10 w-full rounded-lg border border-white/10 bg-[#0b1020] px-3 text-sm font-semibold text-zinc-100 outline-none transition focus:border-cyan-300/40"
                onChange={(event) => onSelectConnection(event.target.value)}
                value={selectedConnectionId}
              >
                {connectionOptions.map((connection) => (
                  <option key={connection.id} value={connection.id}>
                    {connection.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <p className="truncate text-xs font-semibold text-zinc-300">
                {selectedConnection?.engine ?? "Engine"} · {selectedConnection?.host ?? "not connected"}
              </p>
              <p className="mt-2 max-h-10 overflow-hidden text-xs leading-5 text-zinc-500">
                {selectedConnection?.description ?? "Select a connected database to inspect resources."}
              </p>
            </div>
            {activeKind === "relational" ? (
              <details className="group rounded-lg border border-white/10 bg-black/20 p-3">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs font-semibold uppercase text-zinc-400">
                  Refresh schema
                  <ChevronDown className="h-3.5 w-3.5 transition group-open:rotate-180" />
                </summary>
                <div className="mt-3 space-y-3">
                  <label className="block">
                    <span className="text-[0.68rem] font-semibold uppercase text-zinc-600">
                      PostgreSQL URL
                    </span>
                    <input
                      className="mt-2 h-9 w-full rounded-lg border border-white/10 bg-[#0b1020] px-3 text-xs text-zinc-100 outline-none transition placeholder:text-zinc-700 focus:border-cyan-300/40"
                      onChange={(event) => onSourceDatabaseUrlChange(event.target.value)}
                      placeholder="postgresql+psycopg://user:pass@host:5432/db"
                      type="password"
                      value={sourceDatabaseUrl}
                    />
                  </label>
                  <label className="block">
                    <span className="text-[0.68rem] font-semibold uppercase text-zinc-600">
                      Schemas
                    </span>
                    <input
                      className="mt-2 h-9 w-full rounded-lg border border-white/10 bg-[#0b1020] px-3 text-xs text-zinc-100 outline-none transition focus:border-cyan-300/40"
                      onChange={(event) => onSourceSchemaNamesChange(event.target.value)}
                      value={sourceSchemaNames}
                    />
                  </label>
                  <button
                    className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-cyan-300 text-xs font-semibold text-zinc-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-55"
                    disabled={isRefreshingSource}
                    onClick={onRefreshSource}
                  >
                    {isRefreshingSource ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Database className="h-3.5 w-3.5" />
                    )}
                    Refresh tables
                  </button>
                  {sourceRefreshMessage ? (
                    <p className="text-xs leading-5 text-zinc-500">{sourceRefreshMessage}</p>
                  ) : null}
                </div>
              </details>
            ) : null}
            <button
              className="inline-flex h-8 w-full items-center justify-center gap-2 rounded-lg border border-white/10 text-xs font-semibold text-zinc-300 transition hover:border-cyan-300/30 hover:text-cyan-100"
              onClick={onBackToProducts}
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Products
            </button>
          </div>
        </details>

        <details className="group" open>
          <summary className="flex cursor-pointer list-none items-center justify-between px-1">
            <span className="text-xs font-semibold uppercase text-zinc-600">{resourceLabel}</span>
            <span className="inline-flex items-center gap-2 text-xs text-zinc-600">
              {resourceNames.length}
              <ChevronDown className="h-3.5 w-3.5 transition group-open:rotate-180" />
            </span>
          </summary>
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
        </details>
      </div>
    </aside>
  );
}

function WorkspaceOverview({
  connection,
  product,
  run,
  visibleRows,
}: {
  connection: WorkspaceSource | null;
  product: Product | null;
  run: GenerationRun | null;
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
          <h1 className="truncate text-2xl font-semibold text-zinc-950">
            {product?.name ?? "DataBoom workspace"}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-zinc-500">
            <span className="truncate">
              {connection?.name ?? "No database selected"}
            </span>
            <span className="hidden h-1 w-1 rounded-full bg-zinc-300 sm:block" />
            <span className="truncate">
              {connection?.engine ?? kindLabel(product?.kind ?? "relational")}
            </span>
            <span className="hidden h-1 w-1 rounded-full bg-zinc-300 sm:block" />
            <span className="truncate">{connection?.host ?? "local workspace"}</span>
          </div>

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
            icon={Rows3}
            label="Generated"
            value={formatNumber(run?.generated_rows ?? 0)}
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
  downloadFormats,
  onDownloadFormatsChange,
  onViewFormatChange,
  product,
  viewFormat,
}: {
  run: GenerationRun | null;
  activeKind: Product["kind"];
  selectedResource: string | null;
  artifacts: ArtifactList | null;
  downloadFormats: ViewFormat[];
  onDownloadFormatsChange: (formats: ViewFormat[]) => void;
  onViewFormatChange: (format: ViewFormat) => void;
  product: Product | null;
  viewFormat: ViewFormat;
}) {
  const resource =
    run?.tables.find((item) => item.table_name === selectedResource) ??
    run?.collections.find((item) => item.collection_name === selectedResource);
  const selectedView = viewOptions(activeKind).find((option) => option.id === viewFormat);

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
        <ViewFormatMenu
          activeKind={activeKind}
          selectedFormat={selectedView?.id ?? viewOptions(activeKind)[0]?.id ?? "table"}
          onSelect={onViewFormatChange}
        />
        <DownloadFormatMenu
          activeKind={activeKind}
          artifacts={artifacts}
          selectedFormats={downloadFormats}
          onSelectedFormatsChange={onDownloadFormatsChange}
          product={product}
        />
      </div>
    </header>
  );
}

function ViewFormatMenu({
  activeKind,
  selectedFormat,
  onSelect,
}: {
  activeKind: Product["kind"];
  selectedFormat: ViewFormat;
  onSelect: (format: ViewFormat) => void;
}) {
  const options = viewOptions(activeKind);
  const selected = options.find((option) => option.id === selectedFormat) ?? options[0];
  const SelectedIcon = selected?.icon ?? Eye;

  return (
    <details className="group relative">
      <summary className="inline-flex h-9 cursor-pointer list-none items-center gap-2 rounded-md border border-teal-600 bg-teal-600 px-3 text-sm font-semibold text-white transition hover:bg-teal-700">
        <Eye className="h-4 w-4" />
        <span className="hidden sm:inline">View</span>
        <span className="inline-flex items-center gap-1 border-l border-white/20 pl-2">
          <SelectedIcon className="h-3.5 w-3.5" />
          {selected?.label ?? "Preview"}
        </span>
        <ChevronDown className="h-3.5 w-3.5 opacity-80" />
      </summary>
      <div className="absolute right-0 z-30 mt-2 w-64 rounded-xl border border-zinc-200 bg-white p-2 shadow-[0_18px_50px_rgba(15,23,42,0.18)]">
        {options.map((option) => {
          const Icon = option.icon;
          const active = option.id === selectedFormat;
          return (
            <button
              key={option.id}
              className={`flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                active ? "bg-cyan-50 text-cyan-800" : "text-zinc-700 hover:bg-zinc-50"
              }`}
              onClick={(event) => {
                event.currentTarget.closest("details")?.removeAttribute("open");
                onSelect(option.id);
              }}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                <span className="block text-sm font-semibold">{option.label}</span>
                <span className="mt-1 block text-xs leading-5 text-zinc-500">
                  {option.description}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </details>
  );
}

function DownloadFormatMenu({
  activeKind,
  artifacts,
  selectedFormats,
  onSelectedFormatsChange,
  product,
}: {
  activeKind: Product["kind"];
  artifacts: ArtifactList | null;
  selectedFormats: ViewFormat[];
  onSelectedFormatsChange: (formats: ViewFormat[]) => void;
  product: Product | null;
}) {
  const options = downloadOptions(activeKind);
  const selectedCount = selectedFormats.length;
  const hasSelectedArtifacts = selectedFormats.some((format) =>
    Boolean(findArtifactByFormat(artifacts, format)),
  );

  function toggle(format: ViewFormat) {
    if (selectedFormats.includes(format)) {
      const nextFormats = selectedFormats.filter((item) => item !== format);
      onSelectedFormatsChange(nextFormats.length ? nextFormats : [format]);
      return;
    }
    onSelectedFormatsChange([...selectedFormats, format]);
  }

  return (
    <details className="group relative">
      <summary className="inline-flex h-9 cursor-pointer list-none items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm font-semibold text-zinc-700 transition hover:border-cyan-500 hover:text-cyan-700">
        <Download className="h-4 w-4" />
        Download
        <span className="rounded-full bg-cyan-50 px-2 py-0.5 text-[0.68rem] text-cyan-700">
          {selectedCount}
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />
      </summary>
      <div className="absolute right-0 z-30 mt-2 w-72 rounded-xl border border-zinc-200 bg-white p-3 shadow-[0_18px_50px_rgba(15,23,42,0.18)]">
        <div className="mb-3">
          <p className="text-sm font-semibold text-zinc-950">
            {product?.name ?? "Product"} exports
          </p>
          <p className="mt-1 text-xs leading-5 text-zinc-500">
            Select one or more formats, then download matching artifacts.
          </p>
        </div>

        <div className="space-y-1.5">
          {options.map((option) => {
            const Icon = option.icon;
            const checked = selectedFormats.includes(option.id);
            const available = Boolean(findArtifactByFormat(artifacts, option.id));
            return (
              <button
                key={option.id}
                className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left transition ${
                  checked ? "bg-cyan-50 text-cyan-800" : "text-zinc-700 hover:bg-zinc-50"
                }`}
                onClick={() => toggle(option.id)}
              >
                <span className="flex min-w-0 items-center gap-3">
                  <span
                    className={`grid h-5 w-5 place-items-center rounded border ${
                      checked ? "border-cyan-500 bg-cyan-500 text-white" : "border-zinc-300"
                    }`}
                  >
                    {checked ? <Check className="h-3.5 w-3.5" /> : null}
                  </span>
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>
                    <span className="block text-sm font-semibold">{option.label}</span>
                    <span className="text-xs text-zinc-500">
                      {available ? "Artifact ready" : "Generate run first"}
                    </span>
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        <button
          className="mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-zinc-950 text-sm font-semibold text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-45"
          disabled={!hasSelectedArtifacts}
          onClick={() => downloadSelectedArtifacts(artifacts, selectedFormats)}
        >
          <Download className="h-4 w-4" />
          Download selected
        </button>
      </div>
    </details>
  );
}

function DataSurface({
  activeKind,
  documentPreview,
  isGenerating,
  product,
  selectedResource,
  tablePreview,
  viewFormat,
}: {
  activeKind: Product["kind"];
  documentPreview: DocumentPreview | null;
  isGenerating: boolean;
  product: Product | null;
  selectedResource: string | null;
  tablePreview: TablePreview | null;
  viewFormat: ViewFormat;
}) {
  if (activeKind === "document") {
    if (viewFormat === "ndjson") {
      return (
        <TextPreview
          emptyMessage="Generate a Docu-Boom run to preview NDJSON documents."
          isGenerating={isGenerating}
          language="ndjson"
          selectedResource={selectedResource}
          title="NDJSON preview"
          value={documentPreview ? buildNdjsonPreview(documentPreview) : ""}
        />
      );
    }

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

  if (viewFormat === "csv" || viewFormat === "sql") {
    return (
      <TextPreview
        emptyMessage="Generate a relational run to preview this export."
        isGenerating={isGenerating}
        language={viewFormat.toUpperCase()}
        selectedResource={selectedResource}
        title={`${viewFormat.toUpperCase()} preview`}
        value={
          tablePreview
            ? viewFormat === "csv"
              ? buildCsvPreview(tablePreview)
              : buildSqlPreview(tablePreview)
            : ""
        }
      />
    );
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

function TextPreview({
  emptyMessage,
  isGenerating,
  language,
  selectedResource,
  title,
  value,
}: {
  emptyMessage: string;
  isGenerating: boolean;
  language: string;
  selectedResource: string | null;
  title: string;
  value: string;
}) {
  if (!value) {
    return (
      <div className="grid h-full place-items-center px-6 text-center">
        <div>
          <FileText className="mx-auto h-10 w-10 text-zinc-300" />
          <p className="mt-4 text-lg font-semibold text-zinc-950">
            {selectedResource ? shortTableName(selectedResource) : title}
          </p>
          <p className="mt-2 text-sm text-zinc-500">
            {isGenerating ? "Waiting for generated output." : emptyMessage}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-w-0 flex-col bg-zinc-950">
      <div className="flex items-center justify-between border-b border-white/10 bg-[#07111f] px-4 py-3">
        <div>
          <p className="text-sm font-semibold text-white">{title}</p>
          <p className="mt-1 text-xs text-zinc-500">{selectedResource ?? "generated output"}</p>
        </div>
        <span className="rounded-md border border-cyan-300/20 bg-cyan-300/10 px-2 py-1 text-xs font-semibold uppercase text-cyan-100">
          {language}
        </span>
      </div>
      <pre className="workspace-scrollbar-dark min-h-0 flex-1 overflow-auto p-5 text-xs leading-6 text-cyan-50">
        {value}
      </pre>
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

function workspaceConnectionsForProduct(product: Product | null, sources: WorkspaceSource[]) {
  if (!product) {
    return [];
  }
  return sources.filter(
    (source) =>
      source.product_id === product.id &&
      source.kind === product.kind &&
      connectionResources(source, product.kind).length,
  );
}

function connectionResources(connection: WorkspaceSource, kind: Product["kind"]) {
  if (connection.kind !== kind) {
    return [];
  }
  return connection.resources.map((resource) => resource.name);
}

function fallbackWorkspaceSources(products: Product[]) {
  return products.flatMap((product) => {
    const resources = productResources(product);
    if (!resources.length) {
      return [];
    }
    return [
      {
        id: `${product.id}-local-demo`,
        product_id: product.id,
        kind: product.kind,
        name: `${product.name} local demo`,
        engine: fallbackEngine(product.kind),
        host: "local demo source",
        description: "Fallback source built from the product catalog while the workspace API is unavailable.",
        status: product.status === "active" ? "connected" : "planned",
        resources: resources.map((resourceName) => ({
          name: resourceName,
          resource_type: resourceType(product.kind),
          estimated_rows: product.default_row_counts[resourceName] ?? 20,
          columns: [],
        })),
      } satisfies WorkspaceSource,
    ];
  });
}

function fallbackEngine(kind: Product["kind"]) {
  if (kind === "document") {
    return "MongoDB";
  }
  if (kind === "graph") {
    return "Neo4j";
  }
  if (kind === "masking") {
    return "Local files";
  }
  return "PostgreSQL";
}

function resourceType(kind: Product["kind"]) {
  if (kind === "document") {
    return "collection";
  }
  if (kind === "graph") {
    return "graph resource";
  }
  if (kind === "masking") {
    return "policy resource";
  }
  return "table";
}

function viewOptions(kind: Product["kind"]): FormatOption[] {
  if (kind === "document") {
    return [
      {
        id: "json",
        label: "JSON",
        description: "Inspect formatted MongoDB-style documents.",
        extension: ".json",
        icon: FileJson,
      },
      {
        id: "ndjson",
        label: "NDJSON",
        description: "Preview newline-delimited documents for loaders.",
        extension: ".ndjson",
        icon: FileText,
      },
    ];
  }
  if (kind === "graph") {
    return [
      {
        id: "graph",
        label: "Graph",
        description: "Inspect nodes and relationships when Graph-Boom is active.",
        icon: Layers3,
      },
    ];
  }
  if (kind === "masking") {
    return [
      {
        id: "masked",
        label: "Masked",
        description: "Inspect masked records when Masker-Boom is active.",
        icon: PackageCheck,
      },
    ];
  }
  return [
    {
      id: "table",
      label: "Table",
      description: "Inspect rows in a relational grid.",
      icon: Table2,
    },
    {
      id: "csv",
      label: "CSV",
      description: "Preview comma-separated rows for file pipelines.",
      extension: ".csv",
      icon: FileSpreadsheet,
    },
    {
      id: "sql",
      label: "SQL",
      description: "Preview insert statements for database loading.",
      extension: ".sql",
      icon: FileText,
    },
  ];
}

function downloadOptions(kind: Product["kind"]) {
  return viewOptions(kind).filter((option) => option.extension);
}

function findArtifactByFormat(artifacts: ArtifactList | null, format: ViewFormat) {
  const extension = formatExtension(format);
  if (!extension) {
    return null;
  }
  return artifacts?.files.find((file) => file.relative_path.endsWith(extension)) ?? null;
}

async function downloadSelectedArtifacts(
  artifacts: ArtifactList | null,
  selectedFormats: ViewFormat[],
) {
  if (!artifacts) {
    return;
  }

  const selectedArtifacts = selectedFormats
    .map((format) => findArtifactByFormat(artifacts, format))
    .filter((artifact): artifact is ArtifactList["files"][number] => Boolean(artifact));

  for (const artifact of selectedArtifacts) {
    const href = await apiUrl(artifact.download_url);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = artifact.name;
    anchor.rel = "noreferrer";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  }
}

function formatExtension(format: ViewFormat) {
  if (format === "csv") {
    return ".csv";
  }
  if (format === "sql") {
    return ".sql";
  }
  if (format === "json") {
    return ".json";
  }
  if (format === "ndjson") {
    return ".ndjson";
  }
  return null;
}

function buildCsvPreview(preview: TablePreview) {
  const rows = preview.rows.map((row) =>
    preview.columns.map((column) => csvCell(row[column] ?? "")).join(","),
  );
  return [preview.columns.join(","), ...rows].join("\n");
}

function buildSqlPreview(preview: TablePreview) {
  const tableName = shortTableName(preview.table_name);
  const columns = preview.columns.map((column) => `"${column}"`).join(", ");
  return preview.rows
    .map((row) => {
      const values = preview.columns.map((column) => sqlValue(row[column] ?? "")).join(", ");
      return `INSERT INTO "${tableName}" (${columns}) VALUES (${values});`;
    })
    .join("\n");
}

function buildNdjsonPreview(preview: DocumentPreview) {
  return preview.documents.map((document) => JSON.stringify(document)).join("\n");
}

function csvCell(value: string) {
  if (/[",\n]/.test(value)) {
    return `"${value.replaceAll("\"", "\"\"")}"`;
  }
  return value;
}

function sqlValue(value: string) {
  if (/^-?\d+(\.\d+)?$/.test(value)) {
    return value;
  }
  if (value === "") {
    return "NULL";
  }
  return `'${value.replaceAll("'", "''")}'`;
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
