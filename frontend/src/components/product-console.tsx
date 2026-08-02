"use client";

import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  Loader2,
  PackageCheck,
} from "lucide-react";
import Link from "next/link";

import type { ArtifactList, Product, RunArtifact, TablePreview } from "@/lib/api";
import { apiUrl } from "@/lib/api";
import { useEffect, useState } from "react";

export function StatTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
      <p className="text-xs font-semibold uppercase text-zinc-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm text-zinc-500">{hint}</p>
    </div>
  );
}

export function ProductCard({
  product,
  subscribed,
}: {
  product: Product;
  subscribed: boolean;
}) {
  return (
    <Link
      href={`/products/${product.id}`}
      className="block rounded-lg border border-white/10 bg-white/[0.03] p-5 transition hover:border-cyan-300/40 hover:bg-white/[0.06]"
    >
      <div className="flex items-start justify-between gap-4">
        <span className="flex h-11 w-11 items-center justify-center rounded-md bg-cyan-300/10 text-cyan-200">
          <PackageCheck className="h-5 w-5" />
        </span>
        <span
          className={`rounded-md border px-2 py-1 text-xs font-semibold uppercase ${
            subscribed
              ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-200"
              : "border-white/10 bg-white/[0.03] text-zinc-400"
          }`}
        >
          {subscribed ? "Subscribed" : product.status}
        </span>
      </div>
      <p className="mt-6 text-xl font-semibold text-white">{product.name}</p>
      <p className="mt-1 text-sm font-semibold uppercase text-cyan-300">{product.module}</p>
      <p className="mt-4 min-h-12 text-sm leading-6 text-zinc-400">{product.description}</p>
      <div className="mt-6 flex flex-wrap gap-2">
        {product.tables.slice(0, 4).map((table) => (
          <span
            key={table}
            className="rounded-md border border-white/10 px-2 py-1 text-xs text-zinc-500"
          >
            {table}
          </span>
        ))}
      </div>
      <span className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-white">
        Open product <ArrowRight className="h-4 w-4" />
      </span>
    </Link>
  );
}

export function GenerationAnimation({ active }: { active: boolean }) {
  return (
    <div className="rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-5">
      <div className="flex items-center gap-3">
        {active ? (
          <Loader2 className="h-5 w-5 animate-spin text-cyan-200" />
        ) : (
          <CheckCircle2 className="h-5 w-5 text-emerald-200" />
        )}
        <p className="font-semibold text-white">
          {active ? "Generating data..." : "Generator ready"}
        </p>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-4">
        {["Parse schema", "Plan graph", "Write artifacts", "Validate rows"].map((step, index) => (
          <div key={step} className="rounded-md border border-white/10 bg-black/25 p-3">
            <div
              className={`h-1 rounded-full ${
                active ? "animate-pulse bg-cyan-300" : "bg-emerald-300"
              }`}
              style={{ animationDelay: `${index * 130}ms` }}
            />
            <p className="mt-3 text-xs font-semibold uppercase text-zinc-400">{step}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ArtifactButtons({ artifacts }: { artifacts: ArtifactList | null }) {
  if (!artifacts) {
    return null;
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {artifacts.files.map((artifact) => (
        <ArtifactButton key={artifact.relative_path} artifact={artifact} />
      ))}
    </div>
  );
}

function ArtifactButton({ artifact }: { artifact: RunArtifact }) {
  const [href, setHref] = useState("#");
  const Icon = artifact.relative_path.endsWith(".csv")
    ? FileSpreadsheet
    : artifact.relative_path.endsWith(".json")
      ? FileJson
      : FileText;

  useEffect(() => {
    apiUrl(artifact.download_url).then(setHref).catch(() => setHref("#"));
  }, [artifact.download_url]);

  return (
    <a
      className="flex items-center justify-between gap-3 rounded-md border border-white/10 bg-white/[0.03] px-4 py-3 text-sm transition hover:border-emerald-300/35 hover:bg-emerald-300/10"
      href={href}
    >
      <span className="flex min-w-0 items-center gap-3">
        <Icon className="h-4 w-4 shrink-0 text-emerald-200" />
        <span className="truncate text-zinc-300">{artifact.relative_path}</span>
      </span>
      <span className="inline-flex shrink-0 items-center gap-2 text-xs font-semibold uppercase text-emerald-200">
        {formatBytes(artifact.size_bytes)}
        <Download className="h-3.5 w-3.5" />
      </span>
    </a>
  );
}

export function PreviewTable({
  preview,
  defaultOpen = false,
}: {
  preview: TablePreview;
  defaultOpen?: boolean;
}) {
  return (
    <details className="rounded-lg border border-white/10 bg-white/[0.03] p-4" open={defaultOpen}>
      <summary className="cursor-pointer text-sm font-semibold text-white">
        {preview.table_name} · top {preview.rows.length} rows
      </summary>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
          <thead>
            <tr>
              {preview.columns.map((column) => (
                <th
                  key={column}
                  className="border-b border-white/10 px-3 py-2 text-xs font-semibold uppercase text-zinc-500"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((row, index) => (
              <tr key={index}>
                {preview.columns.map((column) => (
                  <td key={column} className="max-w-64 truncate border-b border-white/5 px-3 py-2">
                    {row[column] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-8 text-center">
      <Activity className="mx-auto h-8 w-8 text-zinc-600" />
      <p className="mt-4 font-semibold text-white">{title}</p>
      <p className="mt-2 text-sm text-zinc-500">{detail}</p>
    </div>
  );
}

export function formatBytes(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  return `${(sizeBytes / 1024).toFixed(1)} KB`;
}
