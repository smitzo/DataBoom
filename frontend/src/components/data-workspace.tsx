"use client";

import {
  ArrowLeft,
  Check,
  ChevronDown,
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
  Rows3,
  Search,
  Sparkles,
  Table2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type {
  ArtifactList,
  DocumentPreview,
  GenerationRun,
  GraphPreview,
  PlanProposal,
  Product,
  Subscription,
  TablePreview,
  WorkspaceSourceProfile,
  WorkspaceSource,
} from "@/lib/api";
import {
  apiUrl,
  createProductPlan,
  executeApprovedPlan,
  getDocumentPreview,
  getGraphPreview,
  getProducts,
  getPlans,
  getRun,
  getRunArtifacts,
  getRuns,
  getSubscriptions,
  getTablePreview,
  getWorkspaceSources,
  profileWorkspaceSource,
  refreshWorkspaceSource,
  reviewPlan,
  saveWorkspaceSource,
  subscribeToProduct,
  testWorkspaceConnection,
} from "@/lib/api";
import { getSessionLlmKey } from "@/lib/llm-key";
import type { Session } from "@/lib/session";
import {
  WorkspaceRunPanel,
  type WorkspaceAgentStatus,
  type WorkspaceAgentStep,
  type WorkspaceInsight,
} from "@/components/workspace/workspace-run-panel";

type PreviewMap = Record<string, TablePreview>;
type DocumentPreviewMap = Record<string, DocumentPreview>;
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
  const [plans, setPlans] = useState<PlanProposal[]>([]);
  const [currentPlan, setCurrentPlan] = useState<PlanProposal | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactList | null>(null);
  const [previews, setPreviews] = useState<PreviewMap>({});
  const [documentPreviews, setDocumentPreviews] = useState<DocumentPreviewMap>({});
  const [graphPreview, setGraphPreview] = useState<GraphPreview | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [selectedConnectionId, setSelectedConnectionId] = useState<string>("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedResource, setSelectedResource] = useState<string | null>(null);
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("product");
  const [viewFormat, setViewFormat] = useState<ViewFormat>("table");
  const [downloadFormats, setDownloadFormats] = useState<ViewFormat[]>(["csv"]);
  const [prompt, setPrompt] = useState("Generate realistic data for the selected product");
  const [status, setStatus] = useState<WorkspaceAgentStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [sourceWarning, setSourceWarning] = useState<string | null>(null);
  const [sourceRefreshMessage, setSourceRefreshMessage] = useState<string | null>(null);
  const [sourceProfile, setSourceProfile] = useState<WorkspaceSourceProfile | null>(null);
  const [sourceName, setSourceName] = useState("");
  const [sourceHost, setSourceHost] = useState("");
  const [sourceDatabaseUrl, setSourceDatabaseUrl] = useState("");
  const [sourceSchemaNames, setSourceSchemaNames] = useState("public");
  const [isRefreshingSource, setIsRefreshingSource] = useState(false);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [isSavingSource, setIsSavingSource] = useState(false);
  const [isProfilingSource, setIsProfilingSource] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorkspaceRailCollapsed, setIsWorkspaceRailCollapsed] = useState(false);
  const [isRunPanelOpen, setIsRunPanelOpen] = useState(false);

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
      setGraphPreview(null);
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
      const [nextArtifacts, nextTablePreviews, nextDocumentPreviews, nextGraphPreview] =
        await Promise.all([
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
          activeRun.kind === "graph"
            ? loadGraphPreviewSafe(activeRun.run_id)
            : Promise.resolve(null),
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
      setGraphPreview(nextGraphPreview);
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
  const visibleRows =
    selectedTablePreview?.rows.length ??
    selectedDocumentPreview?.documents.length ??
    (graphPreview ? graphPreview.nodes.length + graphPreview.edges.length : 0);

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
    () => buildAgentSteps(status, selectedRun, selectedProduct, selectedConnection, sourceProfile),
    [selectedProduct, selectedConnection, selectedRun, sourceProfile, status],
  );
  const insight = useMemo(
    () => buildInsight(selectedTablePreview, selectedDocumentPreview),
    [selectedDocumentPreview, selectedTablePreview],
  );
  const workspaceGridClass = isWorkspaceRailCollapsed
    ? isRunPanelOpen
      ? "flex min-h-[calc(100vh-5rem)] flex-col xl:grid xl:grid-cols-[8rem_minmax(0,1fr)_20rem]"
      : "flex min-h-[calc(100vh-5rem)] flex-col xl:grid xl:grid-cols-[8rem_minmax(0,1fr)]"
    : isRunPanelOpen
      ? "flex min-h-[calc(100vh-5rem)] flex-col xl:grid xl:grid-cols-[16rem_minmax(0,1fr)_20rem]"
      : "flex min-h-[calc(100vh-5rem)] flex-col xl:grid xl:grid-cols-[16rem_minmax(0,1fr)]";

  async function loadWorkspace() {
    setIsLoading(true);
    setError(null);
    setSourceWarning(null);
    try {
      const [nextProducts, nextSubscriptions, nextRuns, nextPlans] = await Promise.all([
        getProducts(),
        getSubscriptions(session.token),
        getRuns(),
        getPlans(session.token),
      ]);
      let nextSources: WorkspaceSource[];
      try {
        nextSources = await getWorkspaceSources();
      } catch {
        nextSources = fallbackWorkspaceSources(nextProducts);
        setSourceWarning(
          "Connected sources are unavailable. Showing local workspaces.",
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
      const firstPlan = nextPlans.find((plan) => plan.product_id === firstProductId) ?? null;
      const firstConnection = workspaceConnectionsForProduct(firstProduct, nextSources)[0] ?? null;

      setProducts(nextProducts);
      setWorkspaceSources(nextSources);
      setSubscriptions(nextSubscriptions);
      setRuns(nextRuns);
      setPlans(nextPlans);
      setCurrentPlan(firstPlan);
      if (firstPlan) {
        setPrompt(firstPlan.intent);
      }
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
    setSourceProfile(null);
    const productPlan = plans.find((plan) => plan.product_id === product.id) ?? null;
    setCurrentPlan(productPlan);
    setPrompt(productPlan?.intent ?? "Generate realistic data for the selected product");
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
    setSourceProfile(null);
    setSelectedResource(
      nextConnection ? connectionResources(nextConnection, activeKind)[0] ?? null : null,
    );
  }

  async function testSelectedSourceConnection() {
    if (!sourceDatabaseUrl.trim()) {
      setSourceRefreshMessage("Enter a PostgreSQL connection URL before testing.");
      return;
    }

    setIsTestingConnection(true);
    setSourceRefreshMessage(null);
    try {
      const result = await testWorkspaceConnection(session.token, sourceDatabaseUrl.trim());
      setSourceRefreshMessage(result.message);
    } catch (caughtError) {
      setSourceRefreshMessage(
        caughtError instanceof Error ? caughtError.message : "Unable to test connection",
      );
    } finally {
      setIsTestingConnection(false);
    }
  }

  async function saveSelectedSource() {
    if (!selectedProduct || activeKind !== "relational") {
      setSourceRefreshMessage("Source creation is currently available for Table-Boom.");
      return;
    }
    const cleanName = sourceName.trim();
    if (!cleanName) {
      setSourceRefreshMessage("Enter a source name before saving.");
      return;
    }

    setIsSavingSource(true);
    setSourceRefreshMessage(null);
    try {
      const saved = await saveWorkspaceSource(session.token, {
        id: `${selectedProduct.id}-${slugify(cleanName)}`,
        product_id: selectedProduct.id,
        kind: selectedProduct.kind,
        name: cleanName,
        engine: "PostgreSQL",
        host: sourceHost.trim() || "custom source",
        description: `Operator-created ${selectedProduct.name} source.`,
        status: "connected",
        resources: [],
      });
      setWorkspaceSources((current) => [
        ...current.filter((source) => source.id !== saved.id),
        saved,
      ]);
      setSelectedConnectionId(saved.id);
      setSelectedResource(null);
      setSourceRefreshMessage(`${saved.name} saved. Refresh schema to load tables.`);
    } catch (caughtError) {
      setSourceRefreshMessage(
        caughtError instanceof Error ? caughtError.message : "Unable to save source",
      );
    } finally {
      setIsSavingSource(false);
    }
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
      setSourceProfile(null);
      setSourceRefreshMessage(`Loaded ${refreshed.resources.length} tables from ${refreshed.name}.`);
    } catch (caughtError) {
      setSourceRefreshMessage(
        caughtError instanceof Error ? caughtError.message : "Unable to refresh source",
      );
    } finally {
      setIsRefreshingSource(false);
    }
  }

  async function profileSelectedSource() {
    if (!selectedConnection) {
      return;
    }
    if (activeKind !== "relational") {
      setSourceRefreshMessage("Profiling is currently available for PostgreSQL sources.");
      return;
    }
    if (!sourceDatabaseUrl.trim()) {
      setSourceRefreshMessage("Enter a PostgreSQL connection URL before profiling.");
      return;
    }

    setIsProfilingSource(true);
    setSourceRefreshMessage(null);
    try {
      const profile = await profileWorkspaceSource(session.token, selectedConnection.id, {
        database_url: sourceDatabaseUrl.trim(),
        top_values_limit: 5,
      });
      setSourceProfile(profile);
      setSourceRefreshMessage(
        `Profiled ${profile.tables.length} tables and ${formatNumber(profile.total_rows)} rows.`,
      );
    } catch (caughtError) {
      setSourceRefreshMessage(
        caughtError instanceof Error ? caughtError.message : "Unable to profile source",
      );
    } finally {
      setIsProfilingSource(false);
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

  async function createPlan() {
    if (!selectedProduct) {
      return;
    }
    if (selectedProduct.status !== "active") {
      setError(`${selectedProduct.name} is planned and is not runnable yet`);
      return;
    }

    setIsRunPanelOpen(true);
    setStatus("planning");
    setError(null);
    try {
      const proposal = await createProductPlan(session.token, selectedProduct.id, {
        intent: prompt.trim(),
        row_counts: requestedRowCounts(selectedConnection, selectedProduct),
        seed: `${selectedProduct.id}-workspace`,
        output_formats: downloadOptions(activeKind).map((option) => option.id),
        source_id: workspaceSourceId(selectedConnection),
        user_api_key: getSessionLlmKey() || undefined,
      });
      setPlans((current) => upsertPlan(current, proposal));
      setCurrentPlan(proposal);
      setStatus("idle");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to plan generation");
      setStatus("error");
    }
  }

  async function approveAndGenerate() {
    if (!currentPlan) {
      return;
    }

    setIsRunPanelOpen(true);
    setStatus("planning");
    setError(null);
    try {
      const approved =
        currentPlan.review_status === "draft"
          ? await reviewPlan(session.token, currentPlan.plan_id, "approved")
          : currentPlan;
      setPlans((current) => upsertPlan(current, approved));
      setCurrentPlan(approved);
      setStatus("generating");
      const run = await executeApprovedPlan(
        session.token,
        approved.plan_id,
        workspaceSourceId(selectedConnection),
      );
      setRuns((current) => upsertRun(current, run));
      setSelectedRunId(run.run_id);
      setSelectedResource(runResources(run)[0] ?? null);
      setStatus(runAgentStatus(run));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to generate data");
      setStatus("error");
    }
  }

  async function rejectCurrentPlan() {
    if (!currentPlan || currentPlan.review_status !== "draft") {
      setCurrentPlan(null);
      return;
    }
    setStatus("planning");
    setError(null);
    try {
      const rejected = await reviewPlan(session.token, currentPlan.plan_id, "rejected");
      setPlans((current) => upsertPlan(current, rejected));
      setCurrentPlan(rejected);
      setStatus("idle");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to reject plan");
      setStatus("error");
    }
  }

  function changePrompt(value: string) {
    setPrompt(value);
    if (currentPlan && value !== currentPlan.intent) {
      setCurrentPlan(null);
    }
  }

  if (isLoading) {
    return (
      <div className="grid min-h-[calc(100vh-5rem)] place-items-center rounded-xl border border-white/10 bg-zinc-950">
        <div className="flex items-center gap-3 text-sm font-semibold text-zinc-300">
          <Loader2 className="h-5 w-5 animate-spin text-cyan-200" />
          Loading workspace
        </div>
      </div>
    );
  }

  if (workspaceMode === "catalog" || !selectedProduct) {
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
    <section className="min-h-[calc(100vh-5rem)] overflow-hidden rounded-xl border border-cyan-300/10 bg-[#050917] shadow-[0_20px_70px_rgba(0,0,0,0.32)]">
      <div className={workspaceGridClass}>
        <WorkspaceSidebar
          activeKind={activeKind}
          collapsed={isWorkspaceRailCollapsed}
          connectionOptions={connectionOptions}
          isProfilingSource={isProfilingSource}
          isRefreshingSource={isRefreshingSource}
          isSavingSource={isSavingSource}
          isTestingConnection={isTestingConnection}
          onToggleCollapse={() => setIsWorkspaceRailCollapsed((current) => !current)}
          product={selectedProduct}
          resourceNames={resourceNames}
          selectedConnection={selectedConnection}
          selectedConnectionId={selectedConnectionId}
          selectedResource={selectedResource}
          sourceDatabaseUrl={sourceDatabaseUrl}
          sourceHost={sourceHost}
          sourceName={sourceName}
          sourceProfile={sourceProfile}
          sourceRefreshMessage={sourceRefreshMessage}
          sourceSchemaNames={sourceSchemaNames}
          onBackToProducts={() => setWorkspaceMode("catalog")}
          onProfileSource={profileSelectedSource}
          onRefreshSource={refreshSelectedSource}
          onSaveSource={saveSelectedSource}
          onSelectConnection={chooseConnection}
          onSelectResource={setSelectedResource}
          onSourceDatabaseUrlChange={setSourceDatabaseUrl}
          onSourceHostChange={setSourceHost}
          onSourceNameChange={setSourceName}
          onSourceSchemaNamesChange={setSourceSchemaNames}
          onTestConnection={testSelectedSourceConnection}
        />

        <main className="min-w-0 border-y border-cyan-300/10 bg-[#080d1b] text-zinc-100 xl:border-x xl:border-y-0">
          <WorkspaceOverview
            connection={selectedConnection}
            product={selectedProduct}
            run={selectedRun}
            sourceProfile={sourceProfile}
            visibleRows={visibleRows}
          />
          <WorkspaceToolbar
            run={selectedRun}
            activeKind={activeKind}
            selectedResource={selectedResource}
            artifacts={artifacts}
            downloadFormats={downloadFormats}
            onDownloadFormatsChange={setDownloadFormats}
            onToggleRunPanel={() => setIsRunPanelOpen((current) => !current)}
            onViewFormatChange={setViewFormat}
            runPanelOpen={isRunPanelOpen}
            viewFormat={viewFormat}
          />

          {error ? (
            <div className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm font-medium text-red-700">
              {error}
            </div>
          ) : null}

          <div className="workspace-scrollbar-dark h-[calc(100vh-13.5rem)] min-h-[34rem] overflow-auto bg-[#080d1b]">
            <DataSurface
              activeKind={activeKind}
              documentPreview={selectedDocumentPreview}
              graphPreview={graphPreview}
              isGenerating={selectedRun?.status === "running" || status === "generating"}
              product={selectedProduct}
              selectedResource={selectedResource}
              tablePreview={selectedTablePreview}
              viewFormat={viewFormat}
            />
          </div>
        </main>

        {isRunPanelOpen ? (
          <WorkspaceRunPanel
            currentPlan={currentPlan}
            insight={insight}
            onApproveAndGenerate={approveAndGenerate}
            onClose={() => setIsRunPanelOpen(false)}
            onCreatePlan={createPlan}
            onPromptChange={changePrompt}
            onRejectPlan={rejectCurrentPlan}
            onSubscribe={subscribe}
            prompt={prompt}
            run={selectedRun}
            selectedProduct={selectedProduct}
            status={status}
            steps={agentSteps}
            subscribed={subscribed}
            visibleRows={visibleRows}
          />
        ) : null}
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
    <section className="min-h-[calc(100vh-5rem)] rounded-xl border border-white/10 bg-[#070b16] p-5 shadow-[0_20px_70px_rgba(0,0,0,0.28)] sm:p-7">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col gap-3 border-b border-white/10 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-200">
              Workspaces
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-white sm:text-4xl">
              Choose a data engine
            </h1>
          </div>
          <p className="text-sm text-zinc-500">Table, document, graph, or masking.</p>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {sourceWarning ? (
            <div className="rounded-xl border border-amber-300/25 bg-amber-300/10 px-4 py-3 text-sm text-amber-100 sm:col-span-2">
              {sourceWarning}
            </div>
          ) : null}
          {products.length === 0 ? (
            <div className="rounded-xl border border-red-300/25 bg-red-300/10 p-5 sm:col-span-2">
              <p className="text-lg font-semibold text-red-100">Product catalog did not load.</p>
              <p className="mt-2 text-sm text-red-100/75">{error ?? "Backend unavailable."}</p>
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
                className={`group flex min-h-44 flex-col justify-between rounded-xl border p-5 text-left transition duration-200 ${
                  selected
                    ? "border-cyan-300/45 bg-cyan-300/10 shadow-[0_14px_40px_rgba(34,211,238,0.08)]"
                    : "border-white/10 bg-white/[0.025] hover:-translate-y-0.5 hover:border-cyan-300/30 hover:bg-cyan-300/[0.05]"
                }`}
                onClick={() => onSelectProduct(product)}
              >
                <span>
                  <span className="flex items-start justify-between gap-4">
                    <span className="grid h-11 w-11 place-items-center rounded-xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-100">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span
                      className={`inline-flex items-center gap-2 text-xs font-semibold ${
                        product.status === "active"
                          ? "text-emerald-200"
                          : "text-sky-200"
                      }`}
                    >
                      <span className={`h-2 w-2 rounded-full ${product.status === "active" ? "bg-emerald-300" : "bg-sky-300"}`} />
                      {product.status}
                    </span>
                  </span>
                  <span className="mt-4 block text-xl font-semibold text-white">{product.name}</span>
                  <span className="mt-1 block text-sm text-zinc-500">{kindLabel(product.kind)}</span>
                </span>

                <span className="mt-5 flex items-center justify-between gap-3 border-t border-white/10 pt-3">
                  <span className="text-xs text-zinc-500">
                    {resourceCount} {product.kind === "document" ? "collections" : "resources"}
                  </span>
                  <span className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-100">
                    {subscribed ? "Open" : "Preview"}
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
  isProfilingSource,
  isRefreshingSource,
  isSavingSource,
  isTestingConnection,
  onToggleCollapse,
  product,
  resourceNames,
  selectedConnection,
  selectedConnectionId,
  selectedResource,
  sourceDatabaseUrl,
  sourceHost,
  sourceName,
  sourceProfile,
  sourceRefreshMessage,
  sourceSchemaNames,
  onBackToProducts,
  onProfileSource,
  onRefreshSource,
  onSaveSource,
  onSelectConnection,
  onSelectResource,
  onSourceDatabaseUrlChange,
  onSourceHostChange,
  onSourceNameChange,
  onSourceSchemaNamesChange,
  onTestConnection,
}: {
  activeKind: Product["kind"];
  collapsed: boolean;
  connectionOptions: WorkspaceSource[];
  isProfilingSource: boolean;
  isRefreshingSource: boolean;
  isSavingSource: boolean;
  isTestingConnection: boolean;
  onToggleCollapse: () => void;
  product: Product | null;
  resourceNames: string[];
  selectedConnection: WorkspaceSource | null;
  selectedConnectionId: string;
  selectedResource: string | null;
  sourceDatabaseUrl: string;
  sourceHost: string;
  sourceName: string;
  sourceProfile: WorkspaceSourceProfile | null;
  sourceRefreshMessage: string | null;
  sourceSchemaNames: string;
  onBackToProducts: () => void;
  onProfileSource: () => void;
  onRefreshSource: () => void;
  onSaveSource: () => void;
  onSelectConnection: (connectionId: string) => void;
  onSelectResource: (resourceName: string) => void;
  onSourceDatabaseUrlChange: (value: string) => void;
  onSourceHostChange: (value: string) => void;
  onSourceNameChange: (value: string) => void;
  onSourceSchemaNamesChange: (value: string) => void;
  onTestConnection: () => void;
}) {
  const ResourceIcon =
    activeKind === "document" ? FileJson : activeKind === "graph" ? Layers3 : Table2;
  const ProductIcon = product ? productIcon(product.kind) : Database;
  const resourceLabel =
    activeKind === "document" ? "Collections" : activeKind === "graph" ? "Graph resources" : "Tables";

  if (collapsed) {
    return (
      <aside className="bg-[#060a16] text-zinc-100">
        <div className="grid gap-2 border-b border-cyan-300/10 px-2 py-3">
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
            title="Product catalog"
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
    <aside className="bg-[#060a16] text-zinc-100">
      <div className="border-b border-cyan-300/10 px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <p className="truncate text-sm font-semibold text-white">
            {product?.name ?? kindLabel(activeKind)}
          </p>
          <div className="flex items-center gap-1.5">
            <button
              aria-label="Product catalog"
              className="grid h-9 w-9 place-items-center rounded-lg border border-white/10 text-zinc-400 transition hover:border-cyan-300/30 hover:text-white"
              onClick={onBackToProducts}
              title="Product catalog"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
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
      </div>

      <div className="space-y-4 p-3">
        <details className="group rounded-xl border border-cyan-300/10 bg-white/[0.025] p-3">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
            <span className="flex min-w-0 items-center gap-3">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-emerald-300/25 bg-emerald-300/10 text-emerald-100">
                <Database className="h-4 w-4" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-white">
                  {selectedConnection?.name ?? "Database"}
                </span>
                <span className="mt-1 block truncate text-xs text-zinc-500">
                  {selectedConnection?.engine ?? fallbackEngine(activeKind)} · {connectionOptions.length} sources
                </span>
              </span>
            </span>
            <ChevronDown className="h-4 w-4 shrink-0 text-zinc-500 transition group-open:rotate-180" />
          </summary>

          <div className="mt-4 space-y-3">
            <label className="block">
              <span className="text-[0.68rem] font-semibold uppercase text-zinc-600">
                Database
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
            <div className="rounded-lg border border-emerald-300/15 bg-emerald-300/10 p-3">
              <div className="mb-3 flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 text-xs font-semibold text-emerald-100">
                  <span className="h-2 w-2 rounded-full bg-emerald-300" />
                  Connected
                </span>
              </div>
              <p className="truncate text-xs font-semibold text-zinc-200">
                {selectedConnection?.engine ?? "Engine"} · {selectedConnection?.host ?? "not connected"}
              </p>
              <p className="mt-2 max-h-10 overflow-hidden text-xs leading-5 text-zinc-500">
                {selectedConnection?.description ?? "Select a connected database to inspect resources."}
              </p>
            </div>
            {activeKind === "relational" ? (
              <details className="group rounded-lg border border-white/10 bg-black/20 p-3">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs font-semibold uppercase text-zinc-400">
                  Source connection
                  <ChevronDown className="h-3.5 w-3.5 transition group-open:rotate-180" />
                </summary>
                <div className="mt-3 space-y-3">
                  <div className="grid gap-2">
                    <input
                      className="h-9 w-full rounded-lg border border-white/10 bg-[#0b1020] px-3 text-xs text-zinc-100 outline-none transition placeholder:text-zinc-700 focus:border-cyan-300/40"
                      onChange={(event) => onSourceNameChange(event.target.value)}
                      placeholder="Source name"
                      value={sourceName}
                    />
                    <input
                      className="h-9 w-full rounded-lg border border-white/10 bg-[#0b1020] px-3 text-xs text-zinc-100 outline-none transition placeholder:text-zinc-700 focus:border-cyan-300/40"
                      onChange={(event) => onSourceHostChange(event.target.value)}
                      placeholder="Host label"
                      value={sourceHost}
                    />
                  </div>
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
                  <div className="grid grid-cols-2 gap-2">
                    <SourceActionButton
                      isLoading={isTestingConnection}
                      label="Test"
                      loadingLabel="Testing"
                      onClick={onTestConnection}
                    />
                    <SourceActionButton
                      isLoading={isSavingSource}
                      label="Add"
                      loadingLabel="Saving"
                      onClick={onSaveSource}
                    />
                    <SourceActionButton
                      isLoading={isRefreshingSource}
                      label="Refresh"
                      loadingLabel="Loading"
                      onClick={onRefreshSource}
                    />
                    <SourceActionButton
                      isLoading={isProfilingSource}
                      label="Profile"
                      loadingLabel="Profiling"
                      onClick={onProfileSource}
                    />
                  </div>
                  {sourceRefreshMessage ? (
                    <p className="text-xs leading-5 text-zinc-500">{sourceRefreshMessage}</p>
                  ) : null}
                  {sourceProfile ? <SourceProfileSummary profile={sourceProfile} /> : null}
                </div>
              </details>
            ) : null}
          </div>
        </details>

        <details className="group p-1" open>
          <summary className="flex cursor-pointer list-none items-center justify-between px-1">
            <span className="text-xs font-semibold uppercase text-zinc-600">{resourceLabel}</span>
            <span className="inline-flex items-center gap-2 text-xs text-zinc-600">
              {resourceNames.length}
              <ChevronDown className="h-3.5 w-3.5 transition group-open:rotate-180" />
            </span>
          </summary>
          <div className="workspace-scrollbar-dark mt-3 max-h-[55vh] space-y-1 overflow-auto pr-1">
            {resourceNames.map((tableName) => (
              <button
                key={tableName}
                className={`flex h-11 w-full items-center justify-between gap-2 rounded-lg px-2.5 text-left text-sm transition ${
                  selectedResource === tableName
                    ? "bg-cyan-300/15 text-cyan-100 ring-1 ring-cyan-300/25"
                    : "text-zinc-400 hover:bg-white/[0.05] hover:text-white"
                }`}
                onClick={() => onSelectResource(tableName)}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <ResourceIcon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{shortTableName(tableName)}</span>
                </span>
                <span className="shrink-0 rounded-full bg-white/[0.06] px-2 py-0.5 text-[0.68rem] font-semibold text-zinc-500">
                  {resourceRowCount(selectedConnection, tableName)}
                </span>
              </button>
            ))}
          </div>
        </details>
      </div>
    </aside>
  );
}

function SourceActionButton({
  isLoading,
  label,
  loadingLabel,
  onClick,
}: {
  isLoading: boolean;
  label: string;
  loadingLabel: string;
  onClick: () => void;
}) {
  return (
    <button
      className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-cyan-300/20 bg-cyan-300/10 text-xs font-semibold text-cyan-100 transition hover:border-cyan-300/40 hover:bg-cyan-300/15 disabled:cursor-not-allowed disabled:opacity-55"
      disabled={isLoading}
      onClick={onClick}
    >
      {isLoading ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Database className="h-3.5 w-3.5" />
      )}
      {isLoading ? loadingLabel : label}
    </button>
  );
}

function SourceProfileSummary({ profile }: { profile: WorkspaceSourceProfile }) {
  const firstTable = profile.tables[0];
  const firstColumn = firstTable?.columns[0];

  return (
    <div className="rounded-lg border border-emerald-300/20 bg-emerald-300/10 p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase text-emerald-100">Profile snapshot</p>
        <p className="text-[0.68rem] font-semibold text-emerald-200/70">
          {formatNumber(profile.total_rows)} rows
        </p>
      </div>
      {firstTable ? (
        <p className="mt-2 text-xs leading-5 text-zinc-400">
          {firstTable.schema_name}.{firstTable.name}: {formatNumber(firstTable.row_count)} rows
        </p>
      ) : null}
      {firstColumn ? (
        <p className="mt-1 text-xs leading-5 text-zinc-500">
          {firstColumn.name} null rate {Math.round(firstColumn.null_rate * 100)}%,{" "}
          {formatNumber(firstColumn.distinct_count)} distinct
        </p>
      ) : null}
    </div>
  );
}

function WorkspaceOverview({
  connection,
  product,
  run,
  sourceProfile,
  visibleRows,
}: {
  connection: WorkspaceSource | null;
  product: Product | null;
  run: GenerationRun | null;
  sourceProfile: WorkspaceSourceProfile | null;
  visibleRows: number;
}) {
  const resourceCount = product ? productResources(product).length : 0;
  const plannedRecords = product
    ? Object.values(product.default_row_counts).reduce((total, count) => total + count, 0)
    : 0;
  const progress = run ? progressPercent(run) : 0;
  const runState = runStateLabel(run);
  const schemaLabels = connection ? sourceSchemaLabels(connection) : [];

  return (
    <section className="border-b border-cyan-300/10 bg-[#080d1b]">
      <div className="flex flex-col gap-4 px-4 py-4 sm:px-5 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-100">
            {product ? <Database className="h-5 w-5" /> : <Rows3 className="h-5 w-5" />}
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-xl font-semibold text-white">
                {product?.name ?? "Workspace"}
              </h1>
              {run ? <span className="text-xs font-semibold text-emerald-200">{runState}</span> : null}
            </div>
            <p className="mt-1 truncate text-sm text-zinc-500">
              {connection?.name ?? "No database selected"}
              {schemaLabels.length ? ` · ${schemaLabels.join(", ")}` : ""}
              {sourceProfile ? ` · ${formatNumber(sourceProfile.total_rows)} profiled rows` : ""}
            </p>
          </div>
        </div>

        <dl className="grid grid-cols-4 divide-x divide-white/10 rounded-lg border border-white/10 bg-white/[0.025] py-2 xl:min-w-[28rem]">
          {[
            ["Planned", formatNumber(plannedRecords)],
            [product?.kind === "document" ? "Collections" : "Resources", String(resourceCount)],
            ["Preview", String(visibleRows)],
            ["Generated", formatNumber(run?.generated_rows ?? 0)],
          ].map(([label, value]) => (
            <div className="min-w-0 px-3" key={label}>
              <dt className="truncate text-[0.65rem] font-semibold uppercase text-zinc-600">{label}</dt>
              <dd className="mt-1 truncate text-sm font-semibold text-zinc-200">{value}</dd>
            </div>
          ))}
        </dl>
      </div>
      {run ? (
        <div className="h-0.5 bg-white/[0.06]">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      ) : null}
    </section>
  );
}

function WorkspaceToolbar({
  run,
  activeKind,
  selectedResource,
  artifacts,
  downloadFormats,
  onDownloadFormatsChange,
  onToggleRunPanel,
  onViewFormatChange,
  runPanelOpen,
  viewFormat,
}: {
  run: GenerationRun | null;
  activeKind: Product["kind"];
  selectedResource: string | null;
  artifacts: ArtifactList | null;
  downloadFormats: ViewFormat[];
  onDownloadFormatsChange: (formats: ViewFormat[]) => void;
  onToggleRunPanel: () => void;
  onViewFormatChange: (format: ViewFormat) => void;
  runPanelOpen: boolean;
  viewFormat: ViewFormat;
}) {
  const resource =
    run?.tables.find((item) => item.table_name === selectedResource) ??
    run?.collections.find((item) => item.collection_name === selectedResource);
  const selectedView = viewOptions(activeKind).find((option) => option.id === viewFormat);

  return (
    <header className="border-b border-cyan-300/10 bg-[#080d1b]">
      <div className="flex min-h-16 flex-col gap-3 px-4 py-3 sm:px-5 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="truncate text-lg font-semibold text-white">
              {selectedResource ? shortTableName(selectedResource) : "Data workspace"}
            </h2>
            {resource ? (
              <span className="rounded-md border border-white/10 bg-white/[0.05] px-2 py-1 text-xs font-semibold text-zinc-400">
                {resource.row_count} records
              </span>
            ) : null}
          </div>
          {run ? <p className="mt-1 truncate text-xs text-zinc-500">{run.run_id}</p> : null}
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
          />
          <button
            aria-label={runPanelOpen ? "Close run panel" : "Open run panel"}
            className={`grid h-10 w-10 place-items-center rounded-lg border transition ${
              runPanelOpen
                ? "border-cyan-300/35 bg-cyan-300/12 text-cyan-100"
                : "border-white/10 bg-white/[0.035] text-zinc-300 hover:border-cyan-300/30 hover:text-cyan-100"
            }`}
            onClick={onToggleRunPanel}
            title={runPanelOpen ? "Close run panel" : "Open run panel"}
          >
            <Sparkles className="h-4 w-4" />
          </button>
        </div>
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
      <summary className="inline-flex h-10 cursor-pointer list-none items-center gap-2 rounded-lg border border-cyan-300/25 bg-cyan-300/12 px-3 text-sm font-semibold text-cyan-100 transition hover:border-cyan-300/45 hover:bg-cyan-300/18">
        <Eye className="h-4 w-4" />
        <span className="hidden sm:inline">View</span>
        <span className="inline-flex items-center gap-1 border-l border-white/20 pl-2">
          <SelectedIcon className="h-3.5 w-3.5" />
          {selected?.label ?? "Preview"}
        </span>
        <ChevronDown className="h-3.5 w-3.5 opacity-80" />
      </summary>
      <div className="absolute right-0 z-30 mt-2 w-64 rounded-xl border border-cyan-300/10 bg-[#0b1020] p-2 shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
        {options.map((option) => {
          const Icon = option.icon;
          const active = option.id === selectedFormat;
          return (
            <button
              key={option.id}
              className={`flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                active ? "bg-cyan-300/10 text-cyan-100" : "text-zinc-400 hover:bg-white/[0.05] hover:text-white"
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
}: {
  activeKind: Product["kind"];
  artifacts: ArtifactList | null;
  selectedFormats: ViewFormat[];
  onSelectedFormatsChange: (formats: ViewFormat[]) => void;
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
      <summary className="inline-flex h-10 cursor-pointer list-none items-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] px-3 text-sm font-semibold text-zinc-200 transition hover:border-cyan-300/35 hover:text-cyan-100">
        <Download className="h-4 w-4" />
        Download
        <span className="rounded-full bg-cyan-300/10 px-2 py-0.5 text-[0.68rem] text-cyan-100">
          {selectedCount}
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />
      </summary>
      <div className="absolute right-0 z-30 mt-2 w-72 rounded-xl border border-cyan-300/10 bg-[#0b1020] p-3 shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
        <div className="mb-3">
          <p className="text-sm font-semibold text-white">Export formats</p>
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
                  checked ? "bg-cyan-300/10 text-cyan-100" : "text-zinc-400 hover:bg-white/[0.05] hover:text-white"
                }`}
                onClick={() => toggle(option.id)}
              >
                <span className="flex min-w-0 items-center gap-3">
                  <span
                    className={`grid h-5 w-5 place-items-center rounded border ${
                      checked ? "border-cyan-400 bg-cyan-400 text-slate-950" : "border-zinc-700"
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
          className="mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-cyan-300 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-45"
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
  graphPreview,
  isGenerating,
  product,
  selectedResource,
  tablePreview,
  viewFormat,
}: {
  activeKind: Product["kind"];
  documentPreview: DocumentPreview | null;
  graphPreview: GraphPreview | null;
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

  if (activeKind === "graph") {
    return <GraphPreviewPanel isGenerating={isGenerating} preview={graphPreview} />;
  }

  if (activeKind === "masking") {
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

function GraphPreviewPanel({
  isGenerating,
  preview,
}: {
  isGenerating: boolean;
  preview: GraphPreview | null;
}) {
  const nodes = preview?.nodes ?? [];
  const edges = preview?.edges ?? [];

  if (!preview) {
    return (
      <div className="grid h-full place-items-center px-6 text-center">
        <div>
          <Layers3 className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-4 text-lg font-semibold text-white">Graph preview</p>
          <p className="mt-2 text-sm text-zinc-500">
            {isGenerating
              ? "Waiting for generated nodes and relationships."
              : "Generate a Graph-Boom run to preview nodes and relationships."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-h-full gap-4 p-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <GraphRecordList records={nodes} title={`Nodes · ${nodes.length}`} />
      <GraphRecordList records={edges} title={`Edges · ${edges.length}`} />
    </div>
  );
}

function GraphRecordList({
  records,
  title,
}: {
  records: Record<string, unknown>[];
  title: string;
}) {
  return (
    <section className="rounded-xl border border-cyan-300/15 bg-[#0c1426] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        <Layers3 className="h-4 w-4 text-cyan-300" />
      </div>
      <div className="workspace-scrollbar-dark max-h-[30rem] space-y-3 overflow-auto pr-1">
        {records.map((record, index) => (
          <pre
            className="overflow-auto rounded-lg border border-white/10 bg-black/25 p-3 text-xs leading-5 text-cyan-50"
            key={`${String(record.id ?? "record")}-${index}`}
          >
            {JSON.stringify(record, null, 2)}
          </pre>
        ))}
      </div>
    </section>
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
          <Rows3 className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-4 text-lg font-semibold text-white">
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
    <div className="flex h-full min-w-0 flex-col bg-[#080d1b]">
      <div className="flex flex-col gap-3 border-b border-white/10 bg-[#0a1020] px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <span className="text-xs font-semibold text-zinc-500">{filteredRows.length} preview rows</span>
        <label className="flex h-9 min-w-0 items-center gap-2 rounded-md border border-white/10 bg-white/[0.04] px-3 text-sm text-zinc-500 focus-within:border-cyan-300/45 lg:w-72">
          <Search className="h-4 w-4 shrink-0" />
          <input
            className="min-w-0 flex-1 bg-transparent text-sm text-zinc-100 outline-none placeholder:text-zinc-600"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search preview rows..."
            value={query}
          />
        </label>
      </div>

      <div className="workspace-scrollbar-dark min-h-0 flex-1 overflow-auto bg-[#080d1b]">
        <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
          <thead className="sticky top-0 z-10 bg-[#101727] shadow-[0_1px_0_rgba(255,255,255,0.08)]">
            <tr>
              <th className="w-14 border-b border-r border-white/10 px-3 py-3 text-xs font-semibold text-zinc-500">
                #
              </th>
              {preview.columns.map((column) => (
                <th
                  key={column}
                  className="min-w-44 border-b border-r border-white/10 px-3 py-3 align-bottom"
                >
                  <span className="block text-sm font-semibold text-zinc-100">{column}</span>
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
              const rowTone = rowNumber % 2 === 0 ? "bg-white/[0.035]" : "bg-transparent";
              return (
                <tr key={`${rowNumber}-${rowIndex}`} className={`${rowTone} hover:bg-cyan-300/[0.08]`}>
                  <td className="border-b border-r border-white/[0.06] px-3 py-3 text-xs font-semibold text-zinc-500">
                    {rowNumber}
                  </td>
                  {preview.columns.map((column) => (
                    <td
                      key={column}
                      className="max-w-72 truncate border-b border-r border-white/[0.06] px-3 py-3 text-zinc-300"
                      title={row[column] ?? ""}
                    >
                      {column === "status" ? (
                        <span className={`rounded-md px-2 py-1 text-xs font-semibold ${statusBadgeClass(row[column] ?? "")}`}>
                          {row[column] ?? ""}
                        </span>
                      ) : (
                        row[column] ?? ""
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-white/10 bg-[#0a1020] px-4 py-3 text-xs font-semibold text-zinc-500 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <span>Rows per page</span>
          <select
            className="h-8 rounded-md border border-white/10 bg-[#080d1b] px-2 text-xs font-semibold text-zinc-200 outline-none focus:border-cyan-300/45"
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
            className="h-8 rounded-md border border-white/10 px-2.5 text-zinc-400 transition hover:border-cyan-300/35 hover:text-cyan-100 disabled:cursor-not-allowed disabled:opacity-40"
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
                    ? "border-cyan-300/45 bg-cyan-300/10 text-cyan-100"
                    : "border-white/10 text-zinc-400 hover:border-cyan-300/35 hover:text-cyan-100"
                }`}
                onClick={() => setPage(item)}
              >
                {item}
              </button>
            ),
          )}
          <button
            className="h-8 rounded-md border border-white/10 px-2.5 text-zinc-400 transition hover:border-cyan-300/35 hover:text-cyan-100 disabled:cursor-not-allowed disabled:opacity-40"
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
          <FileText className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-4 text-lg font-semibold text-white">
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
          <Rows3 className="mx-auto h-10 w-10 text-zinc-600" />
          <p className="mt-4 text-lg font-semibold text-white">
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
        <article key={index} className="rounded-xl border border-white/10 bg-white/[0.035]">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
            <p className="text-xs font-semibold uppercase text-zinc-500">Document {index + 1}</p>
            <p className="text-xs font-semibold text-zinc-500">{preview.collection_name}</p>
          </div>
          <pre className="workspace-scrollbar-dark max-h-96 overflow-auto p-4 text-xs leading-5 text-zinc-200">
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
        <Sparkles className="mx-auto h-10 w-10 text-zinc-600" />
        <p className="mt-4 text-lg font-semibold text-white">
          {product?.name ?? "Planned product"}
        </p>
        <p className="mt-2 text-sm leading-6 text-zinc-500">
          This engine is not available in the current release.
        </p>
      </div>
    </div>
  );
}

type AgentStep = WorkspaceAgentStep;
type Insight = WorkspaceInsight;

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

async function loadGraphPreviewSafe(runId: string) {
  try {
    return await getGraphPreview(runId, 20, 20);
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

function upsertPlan(plans: PlanProposal[], plan: PlanProposal) {
  const remaining = plans.filter((item) => item.plan_id !== plan.plan_id);
  return [plan, ...remaining];
}

function requestedRowCounts(connection: WorkspaceSource | null, product: Product) {
  const counts = connection
    ? Object.fromEntries(
        connection.resources.map((resource) => [
          resource.name,
          Math.min(Math.max(resource.estimated_rows, 0), 1_000_000),
        ]),
      )
    : product.default_row_counts;
  return counts;
}

function workspaceSourceId(connection: WorkspaceSource | null) {
  if (!connection || connection.id.endsWith("-local-demo")) {
    return undefined;
  }
  return connection.id;
}

function runAgentStatus(run: GenerationRun): WorkspaceAgentStatus {
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

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function sourceSchemaLabels(connection: WorkspaceSource) {
  return Array.from(
    new Set(
      connection.resources
        .map((resource) => resource.schema_name)
        .filter((schemaName): schemaName is string => Boolean(schemaName)),
    ),
  );
}

function slugify(value: string) {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug || "source";
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

function statusBadgeClass(status: string) {
  const normalizedStatus = status.toLowerCase();
  if (["posted", "completed", "active", "success"].includes(normalizedStatus)) {
    return "border border-cyan-300/20 bg-cyan-300/10 text-cyan-100";
  }
  if (["pending", "queued", "processing"].includes(normalizedStatus)) {
    return "border border-amber-300/20 bg-amber-300/10 text-amber-100";
  }
  if (["failed", "blocked", "rejected"].includes(normalizedStatus)) {
    return "border border-red-300/20 bg-red-300/10 text-red-100";
  }
  if (["reversed", "refunded"].includes(normalizedStatus)) {
    return "border border-fuchsia-300/20 bg-fuchsia-300/10 text-fuchsia-100";
  }
  return "border border-white/10 bg-white/[0.06] text-zinc-300";
}

function resourceRowCount(connection: WorkspaceSource | null, resourceName: string) {
  const rowCount = connection?.resources.find((resource) => resource.name === resourceName)?.estimated_rows;
  return rowCount === undefined ? "-" : formatNumber(rowCount);
}

function delay(milliseconds: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function buildAgentSteps(
  status: WorkspaceAgentStatus,
  run: GenerationRun | null,
  product: Product | null,
  connection: WorkspaceSource | null,
  profile: WorkspaceSourceProfile | null,
): AgentStep[] {
  const completed = status === "complete" || run?.status === "completed";
  const running = status === "generating" || run?.status === "running";
  const sourceReady = product ? product.kind !== "relational" || Boolean(connection) : false;
  const schemaReady = product
    ? product.kind !== "relational" || Boolean(connection?.resources.length)
    : false;
  const profileReady = product ? product.kind !== "relational" || Boolean(profile) : false;
  const resourceCount =
    connection?.resources.length || (product ? productResources(product).length : 0);
  const resourceLabel =
    product?.kind === "document"
      ? "collections"
      : product?.kind === "graph"
        ? "graph resources"
        : "resources";
  const contractLabel =
    product?.kind === "document"
      ? "Load document contract"
      : product?.kind === "graph"
        ? "Load graph contract"
        : "Refresh schema contract";
  const resolveLabel =
    product?.kind === "document"
      ? "Resolve document shape"
      : product?.kind === "graph"
        ? "Resolve graph endpoints"
        : "Profile and resolve keys";
  const generateLabel =
    product?.kind === "document"
      ? "Generate documents"
      : product?.kind === "graph"
        ? "Generate nodes and edges"
        : "Generate rows";

  return [
    {
      label: "Select source",
      detail:
        product && connection
          ? `${connection.name} drives ${product.name}`
          : product
            ? `${product.name} workspace selected`
            : "Waiting for product workspace",
      state: sourceReady ? "done" : "waiting",
    },
    {
      label: contractLabel,
      detail:
        product && connection?.refreshed_at
          ? `${resourceCount} ${resourceLabel}, refreshed ${formatDateTime(
              connection.refreshed_at,
            )}`
          : product
            ? `${resourceCount} ${resourceLabel} available`
            : "Waiting for schema metadata",
      state: schemaReady ? "done" : running ? "active" : "waiting",
    },
    {
      label: resolveLabel,
      detail:
        profile
          ? `${formatNumber(profile.total_rows)} source rows profiled`
          : product?.kind === "document"
            ? "Object IDs, nested arrays, and collection references"
            : product?.kind === "graph"
              ? "Stable node IDs, edge types, and valid source/target labels"
              : "Optional profiling plus primary and foreign keys",
      state: profileReady || run ? "done" : running ? "active" : "waiting",
    },
    {
      label: generateLabel,
      detail: run
        ? `${formatNumber(run.generated_rows)} / ${formatNumber(run.total_rows)} records`
        : "Local artifact stream",
      state: completed ? "done" : running ? "active" : "waiting",
    },
    {
      label: "Validate, time, and export",
      detail: run?.validation?.passed
        ? `${run.operation_timings.length} timed operations, validation passed`
        : "Awaiting validation report and operation timings",
      state: completed && run?.validation?.passed ? "done" : running ? "active" : "waiting",
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
  if (run.kind === "graph") {
    return Boolean(run.graph);
  }
  const runResourceNames = new Set(runResources(run).map(shortTableName));
  return productResources(product).some((resource) => runResourceNames.has(resource));
}

function runResources(run: GenerationRun) {
  if (run.kind === "document") {
    return run.collections.map((collection) => collection.collection_name);
  }
  if (run.kind === "graph" && run.graph) {
    return ["nodes", "edges"];
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
  if (run.kind === "graph" && run.graph) {
    return [
      { name: "nodes", rowCount: run.graph.node_count },
      { name: "edges", rowCount: run.graph.edge_count },
    ];
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
      source.kind === product.kind,
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
        schema_ddl: null,
        refreshed_at: null,
        resources: resources.map((resourceName) => ({
          name: resourceName,
          resource_type: resourceType(product.kind),
          estimated_rows: product.default_row_counts[resourceName] ?? 20,
          columns: [],
          schema_name: null,
          primary_key: [],
          foreign_keys: [],
          unique_constraints: [],
          column_details: [],
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
  if (product.kind === "graph") {
    return Object.keys(product.default_row_counts);
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
