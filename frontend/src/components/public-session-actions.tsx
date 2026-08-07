"use client";

import { ArrowRight, Play } from "lucide-react";
import { useEffect, useState } from "react";

import { loadSession } from "@/lib/session";

export function PublicHeaderActions() {
  const loggedIn = useLoggedIn();

  if (loggedIn === null) {
    return <div className="hidden h-11 w-48 md:block" />;
  }

  return (
    <div className="hidden items-center gap-3 md:flex">
      {loggedIn ? (
        <a
          href="/dashboard"
          className="inline-flex h-11 items-center rounded-full bg-emerald-300 px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
        >
          My dashboard
        </a>
      ) : (
        <>
          <a
            href="/login"
            className="inline-flex h-11 items-center rounded-full border border-[color:var(--border)] px-5 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[var(--surface)]"
          >
            Log in
          </a>
          <a
            href="/login"
            className="inline-flex h-11 items-center rounded-full bg-emerald-300 px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
          >
            Start generating
          </a>
        </>
      )}
    </div>
  );
}

export function HeroActions() {
  const loggedIn = useLoggedIn();

  if (loggedIn === null) {
    return <div className="h-12 w-64 rounded-md border border-[color:var(--border)] bg-[var(--surface)]" />;
  }

  if (loggedIn) {
    return (
      <a
        href="/dashboard"
        className="inline-flex h-12 items-center gap-2 rounded-md bg-emerald-300 px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
      >
        My dashboard
        <ArrowRight className="h-4 w-4" />
      </a>
    );
  }

  return (
    <>
      <a
        href="/login"
        className="inline-flex h-12 items-center gap-2 rounded-md bg-emerald-300 px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
      >
        <Play className="h-4 w-4" />
        Start generating
      </a>
      <a
        href="/dashboard"
        className="inline-flex h-12 items-center gap-2 rounded-md border border-[color:var(--border)] px-6 text-sm font-semibold text-[color:var(--text-primary)] transition hover:bg-[var(--surface)]"
      >
        My dashboard
        <ArrowRight className="h-4 w-4" />
      </a>
    </>
  );
}

function useLoggedIn() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    setLoggedIn(Boolean(loadSession()));
  }, []);

  return loggedIn;
}
