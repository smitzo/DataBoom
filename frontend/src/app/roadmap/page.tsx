"use client";

import { CheckCircle2, Circle, Clock3 } from "lucide-react";

import { PageHeader } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { roadmap, type RoadmapItem } from "@/data/workbench";

export default function RoadmapPage() {
  return (
    <AuthGate>
      {() => <RoadmapContent />}
    </AuthGate>
  );
}

function RoadmapContent() {
  return (
    <>
      <PageHeader
        eyebrow="Roadmap"
        title="Product phases stay visible."
        description="As major backend and frontend capabilities land, they move into achieved steps while future phases remain explicit."
      />

      <div className="space-y-4">
        {roadmap.map((item) => (
          <RoadmapCard key={item.phase} item={item} />
        ))}
      </div>
    </>
  );
}

function RoadmapCard({ item }: { item: RoadmapItem }) {
  const Icon = item.status === "achieved" ? CheckCircle2 : item.status === "next" ? Clock3 : Circle;

  return (
    <article className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase text-cyan-300">{item.phase}</p>
          <h2 className="mt-2 text-xl font-semibold text-white">{item.title}</h2>
          <p className="mt-3 max-w-4xl text-sm leading-6 text-zinc-400">{item.description}</p>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-md border border-white/10 bg-black/25 px-3 py-2 text-xs font-semibold uppercase text-zinc-300">
          <Icon className="h-4 w-4" />
          {item.status}
        </span>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <RoadmapList title="Achieved" items={item.achieved} empty="No completed work yet." />
        <RoadmapList title="Future" items={item.future} empty="No future steps listed." />
      </div>
    </article>
  );
}

function RoadmapList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="rounded-md border border-white/10 bg-black/25 p-4">
      <p className="text-sm font-semibold text-white">{title}</p>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? (
          items.map((item) => (
            <p key={item} className="text-sm leading-6 text-zinc-400">
              {item}
            </p>
          ))
        ) : (
          <p className="text-sm text-zinc-600">{empty}</p>
        )}
      </div>
    </div>
  );
}
