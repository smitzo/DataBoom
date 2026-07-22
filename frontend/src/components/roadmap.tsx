"use client";

import { CheckCircle2, Circle, Clock3 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Section } from "@/components/layout";
import { roadmap } from "@/data/workbench";
import type { RoadmapItem, RoadmapStatus } from "@/data/workbench";

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
  const itemRefs = useRef<Array<HTMLElement | null>>([]);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const updateActiveIndex = () => {
      const activationLine = window.innerHeight * 0.58;
      let nextIndex = 0;

      itemRefs.current.forEach((node, index) => {
        if (!node) {
          return;
        }

        if (node.getBoundingClientRect().top <= activationLine) {
          nextIndex = index;
        }
      });

      setActiveIndex(nextIndex);
    };

    updateActiveIndex();
    window.addEventListener("scroll", updateActiveIndex, { passive: true });
    window.addEventListener("resize", updateActiveIndex);

    return () => {
      window.removeEventListener("scroll", updateActiveIndex);
      window.removeEventListener("resize", updateActiveIndex);
    };
  }, []);

  return (
    <Section
      id="roadmap"
      eyebrow="Roadmap"
      title="Every major capability becomes a visible milestone."
      subtitle="As each phase lands, important functionality moves from upcoming work into achieved steps so the product story stays current."
    >
      <div className="relative">
        <div className="space-y-6">
          {roadmap.map((item, index) => (
            <RoadmapTimelineItem
              key={item.phase}
              item={item}
              index={index}
              activeIndex={activeIndex}
              isLast={index === roadmap.length - 1}
              setNode={(node) => {
                itemRefs.current[index] = node;
              }}
            />
          ))}
        </div>
      </div>
    </Section>
  );
}

function RoadmapTimelineItem({
  item,
  index,
  activeIndex,
  isLast,
  setNode,
}: {
  item: RoadmapItem;
  index: number;
  activeIndex: number;
  isLast: boolean;
  setNode: (node: HTMLElement | null) => void;
}) {
  const isActive = index <= activeIndex;
  const segmentActive = index < activeIndex;

  return (
    <article ref={setNode} className="relative grid gap-4 md:grid-cols-[72px_1fr]">
      <div className="relative flex justify-center">
        {!isLast ? (
          <span
            className={`absolute top-16 bottom-[-1.5rem] w-px transition-colors duration-500 ${
              segmentActive
                ? "bg-gradient-to-b from-cyan-300 via-indigo-400 to-fuchsia-500 shadow-[0_0_24px_rgba(34,211,238,0.75)]"
                : "bg-white/10"
            }`}
          />
        ) : null}
        <span
          className={`relative z-10 flex h-14 w-14 items-center justify-center rounded-lg border transition duration-500 ${
            isActive
              ? "border-cyan-300/60 bg-cyan-300/10 text-cyan-200 shadow-[0_0_28px_rgba(34,211,238,0.45)]"
              : "border-white/10 bg-white/[0.03] text-zinc-500"
          }`}
        >
          <StatusIcon status={item.status} />
        </span>
      </div>

      <div
        className={`rounded-lg border p-5 transition duration-500 ${
          isActive
            ? "border-cyan-300/35 bg-white/[0.05] shadow-2xl shadow-cyan-950/20"
            : "border-white/10 bg-white/[0.03]"
        }`}
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase text-zinc-500">{item.phase}</p>
            <h3 className="mt-2 text-xl font-semibold text-white">{item.title}</h3>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-400">
              {item.description}
            </p>
          </div>
          <span
            className={`inline-flex w-fit items-center gap-2 rounded-md border px-3 py-2 text-xs font-semibold uppercase ${statusCopy[item.status].className}`}
          >
            <StatusIcon status={item.status} />
            {statusCopy[item.status].label}
          </span>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <RoadmapList
            title="Achieved steps"
            items={item.achieved}
            empty="Nothing shipped in this phase yet."
          />
          <RoadmapList title="Future steps" items={item.future} empty="No future steps listed." />
        </div>
      </div>
    </article>
  );
}

function StatusIcon({ status }: { status: RoadmapStatus }) {
  if (status === "achieved") {
    return <CheckCircle2 className="h-4 w-4" />;
  }

  if (status === "next") {
    return <Clock3 className="h-4 w-4" />;
  }

  return <Circle className="h-4 w-4" />;
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
