import { CheckCircle2, Circle, Clock3 } from "lucide-react";

import { Section } from "@/components/layout";
import { roadmap } from "@/data/workbench";
import type { RoadmapStatus } from "@/data/workbench";

const statusCopy: Record<RoadmapStatus, { label: string; className: string }> = {
  achieved: {
    label: "Achieved",
    className: "border-emerald-300/30 bg-emerald-300/10 text-emerald-200",
  },
  next: {
    label: "Next",
    className: "border-sky-300/30 bg-sky-300/10 text-sky-200",
  },
  planned: {
    label: "Planned",
    className: "border-white/10 bg-white/[0.03] text-zinc-300",
  },
};

export function Roadmap() {
  return (
    <Section
      id="roadmap"
      eyebrow="Roadmap"
      title="Every major capability becomes a visible milestone."
      subtitle="As each phase lands, important functionality moves from upcoming work into achieved steps so the product story stays current."
    >
      <div className="space-y-4">
        {roadmap.map((item) => (
          <article key={item.phase} className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase text-zinc-500">{item.phase}</p>
                <h3 className="mt-2 text-xl font-semibold text-white">{item.title}</h3>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-400">
                  {item.description}
                </p>
              </div>
              <span className={`inline-flex w-fit items-center gap-2 rounded-md border px-3 py-2 text-xs font-semibold uppercase ${statusCopy[item.status].className}`}>
                {item.status === "achieved" ? <CheckCircle2 className="h-4 w-4" /> : null}
                {item.status === "next" ? <Clock3 className="h-4 w-4" /> : null}
                {item.status === "planned" ? <Circle className="h-4 w-4" /> : null}
                {statusCopy[item.status].label}
              </span>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <RoadmapList title="Achieved steps" items={item.achieved} empty="Nothing shipped in this phase yet." />
              <RoadmapList title="Future steps" items={item.future} empty="No future steps listed." />
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}

function RoadmapList({
  title,
  items,
  empty,
}: {
  title: string;
  items: string[];
  empty: string;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/25 p-4">
      <p className="text-sm font-semibold text-white">{title}</p>
      <div className="mt-4 space-y-3">
        {items.length > 0 ? (
          items.map((item) => (
            <div key={item} className="flex gap-3">
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-emerald-300" />
              <p className="text-sm leading-6 text-zinc-400">{item}</p>
            </div>
          ))
        ) : (
          <p className="text-sm leading-6 text-zinc-600">{empty}</p>
        )}
      </div>
    </div>
  );
}
