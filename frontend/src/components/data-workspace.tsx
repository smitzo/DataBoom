"use client";

import {
  CheckCircle2,
  ChevronDown,
  CircleAlert,
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

import { BrandLogo } from "@/components/brand";
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
    <section className="min-h-[calc(100vh-6rem)] overflow-hidden rounded-xl border border-white/10 bg-zinc-950 shadow-[0_24px_80px_rgba(0,0,0,0.32)]">
      <div className="flex min-h-[calc(100vh-6rem)] flex-col xl:grid xl:grid-cols-[17rem_minmax(0,1fr)_26rem]">
        <WorkspaceSidebar
          activeKind={activeKind}
          products={products}
          selectedProductId={selectedProductId}
          subscribedProductIds={subscribedProductIds}
          resourceNames={resourceNames}
          selectedResource={selectedResource}
          onSelectProduct={chooseProduct}
          onSelectResource={setSelectedResource}
        />

        <main className="min-w-0 border-y border-white/10 bg-zinc-100 text-zinc-950 xl:border-x xl:border-y-0">
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

          <div className="h-[calc(100vh-13rem)] min-h-[34rem] overflow-auto bg-white">
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
  products,
  selectedProductId,
  subscribedProductIds,
  resourceNames,
  selectedResource,
  onSelectProduct,
  onSelectResource,
}: {
  activeKind: Product["kind"];
  products: Product[];
  selectedProductId: string;
  subscribedProductIds: Set<string>;
  resourceNames: string[];
  selectedResource: string | null;
  onSelectProduct: (product: Product) => void;
  onSelectResource: (resourceName: string) => void;
}) {
  const ResourceIcon = activeKind === "document" ? FileJson : Table2;

  return (
    <aside className="bg-[#090b13] text-zinc-100">
      <div className="border-b border-white/10 px-4 py-5">
        <BrandLogo
          href={null}
          size="sm"
          sublabel={kindLabel(activeKind)}
          className="[--text-primary:#ffffff] [--text-faint:#71717a]"
        />
      </div>

      <div className="space-y-5 p-3">
        <div>
          <p className="px-2 text-xs font-semibold uppercase text-zinc-600">Datasets</p>
          <div className="mt-2 space-y-1">
            {products.map((product) => (
              <button
                key={product.id}
                className={`flex h-11 w-full items-center gap-2 rounded-md px-2.5 text-left text-sm transition ${
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
            <p className="text-xs font-semibold uppercase text-zinc-600">
              {activeKind === "document" ? "Collections" : "Resources"}
            </p>
            <span className="text-xs text-zinc-600">{resourceNames.length}</span>
          </div>
          <div className="mt-2 space-y-1">
            {resourceNames.map((tableName) => (
              <button
                key={tableName}
                className={`flex h-10 w-full items-center gap-2 rounded-md px-2.5 text-left text-sm transition ${
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
    <header className="flex min-h-16 flex-col gap-3 border-b border-zinc-200 bg-white px-5 py-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="truncate text-xl font-semibold text-zinc-950">
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
        <ToolbarPill active icon={Table2} label={activeKind === "document" ? "Document" : "Table"} />
        <ArtifactShortcut artifacts={artifacts} extension=".json" icon={FileJson} label="JSON" />
        <ArtifactShortcut artifacts={artifacts} extension=".ndjson" icon={FileText} label="NDJSON" />
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
          <pre className="max-h-96 overflow-auto p-4 text-xs leading-5 text-zinc-800">
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
      <div className="border-b border-zinc-200 bg-white px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase text-zinc-400">Agent workspace</p>
            <h2 className="mt-1 truncate text-lg font-semibold text-zinc-950">
              DataBoom Workspace
            </h2>
          </div>
          <span
            className={`inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs font-semibold ${runStateClass}`}
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
                disabled={busy || !selectedProduct || selectedProduct.status !== "active"}
                onClick={onGenerate}
              >
                {status === "generating" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                {status === "generating" ? "Generating" : "Run"}
              </button>
            ) : (
              <button
                className="inline-flex h-9 items-center gap-2 rounded-md bg-cyan-700 px-3 text-sm font-semibold text-white transition hover:bg-cyan-600 disabled:cursor-not-allowed disabled:opacity-60"
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
