"use client";

import { CheckCircle2, Circle, Clock3 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export type TimelineStatus = "achieved" | "next" | "planned";

export type TimelineSection = {
  title: string;
  items: string[];
  empty: string;
};

export type TimelineItem = {
  id: string;
  eyebrow: string;
  status: TimelineStatus;
  title: string;
  description: string;
  sections: TimelineSection[];
};

const statusCopy: Record<TimelineStatus, { label: string; className: string }> = {
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
    className: "border-[color:var(--border)] bg-[var(--surface)] text-[color:var(--text-secondary)]",
  },
};

export function Timeline({ items }: { items: TimelineItem[] }) {
  const sectionRef = useRef<HTMLDivElement | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const updateProgress = () => {
      if (!sectionRef.current) {
        return;
      }

      const rect = sectionRef.current.getBoundingClientRect();
      const startLine = window.innerHeight * 0.72;
      const endLine = window.innerHeight * 0.28;
      const travel = Math.max(rect.height - (startLine - endLine), 1);
      const nextProgress = Math.min(Math.max((startLine - rect.top) / travel, 0), 1);
      const nextActiveIndex = Math.min(
        Math.floor(nextProgress * Math.max(items.length - 1, 1) + 0.001),
        items.length - 1,
      );

      setProgress(nextProgress);
      setActiveIndex(nextActiveIndex);
    };

    updateProgress();
    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);

    return () => {
      window.removeEventListener("scroll", updateProgress);
      window.removeEventListener("resize", updateProgress);
    };
  }, [items.length]);

  return (
    <div ref={sectionRef} className="relative">
      <TimelineTrack progress={progress} />
      <div className="relative z-10 space-y-8">
        {items.map((item, index) => (
          <TimelineCard
            key={item.id}
            item={item}
            active={index <= activeIndex}
          />
        ))}
      </div>
    </div>
  );
}

function TimelineCard({ item, active }: { item: TimelineItem; active: boolean }) {
  return (
    <article className="relative grid grid-cols-[68px_1fr] gap-4 md:grid-cols-[80px_1fr]">
      <div className="relative flex justify-center">
        <span
          className={`relative z-10 flex h-16 w-16 items-center justify-center rounded-xl border transition duration-500 ${
            active
              ? "border-cyan-300/60 bg-[var(--section-bg)] text-cyan-400 shadow-[0_0_28px_rgba(34,211,238,0.35)]"
              : "border-[color:var(--border)] bg-[var(--section-bg)] text-[color:var(--text-faint)]"
          }`}
        >
          <StatusIcon status={item.status} />
        </span>
      </div>

      <div
        className={`rounded-xl border p-5 transition duration-500 ${
          active
            ? "border-cyan-300/35 bg-[var(--surface-strong)] shadow-2xl shadow-cyan-950/20"
            : "border-[color:var(--border)] bg-[var(--surface)]"
        }`}
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase text-[color:var(--text-faint)]">
              {item.eyebrow}
            </p>
            <h3 className="mt-2 text-xl font-semibold text-[color:var(--text-primary)]">
              {item.title}
            </h3>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[color:var(--text-muted)]">
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
          {item.sections.map((section) => (
            <TimelineList key={section.title} section={section} />
          ))}
        </div>
      </div>
    </article>
  );
}

function TimelineTrack({ progress }: { progress: number }) {
  return (
    <div
      className="pointer-events-none absolute bottom-8 left-[34px] top-16 z-0 w-px overflow-hidden bg-[var(--border)] md:left-10"
      aria-hidden="true"
    >
      <span
        className="block w-px bg-gradient-to-b from-emerald-300 via-cyan-300 to-sky-300 shadow-[0_0_18px_rgba(34,211,238,0.75)] transition-[height] duration-150 ease-out"
        style={{ height: `${Math.round(progress * 100)}%` }}
      />
    </div>
  );
}

function StatusIcon({ status }: { status: TimelineStatus }) {
  if (status === "achieved") {
    return <CheckCircle2 className="h-4 w-4" />;
  }

  if (status === "next") {
    return <Clock3 className="h-4 w-4" />;
  }

  return <Circle className="h-4 w-4" />;
}

function TimelineList({ section }: { section: TimelineSection }) {
  return (
    <div className="rounded-xl border border-[color:var(--border)] bg-[var(--surface-muted)] p-4">
      <p className="text-sm font-semibold text-[color:var(--text-primary)]">{section.title}</p>
      <div className="mt-4 space-y-3">
        {section.items.length > 0 ? (
          section.items.map((item) => (
            <div key={item} className="flex gap-3">
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-emerald-300" />
              <p className="text-sm leading-6 text-[color:var(--text-muted)]">{item}</p>
            </div>
          ))
        ) : (
          <p className="text-sm leading-6 text-[color:var(--text-faint)]">{section.empty}</p>
        )}
      </div>
    </div>
  );
}
