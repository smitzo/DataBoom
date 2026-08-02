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
          className="inline-flex h-11 items-center rounded-full bg-white px-6 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-100"
        >
          My dashboard
        </a>
      ) : (
        <>
          <a
            href="/login"
            className="inline-flex h-11 items-center rounded-full border border-white/10 px-5 text-sm font-semibold text-white transition hover:border-white/30"
          >
            Log in
          </a>
          <a
            href="/login"
            className="inline-flex h-11 items-center rounded-full bg-white px-6 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-100"
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
    return <div className="h-12 w-64 rounded-md border border-white/10 bg-white/[0.04]" />;
  }

  if (loggedIn) {
    return (
      <a
        href="/dashboard"
        className="inline-flex h-12 items-center gap-2 rounded-md bg-white px-6 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-100"
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
        className="inline-flex h-12 items-center gap-2 rounded-md bg-white px-6 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-100"
      >
        <Play className="h-4 w-4" />
        Start generating
      </a>
      <a
        href="/dashboard"
        className="inline-flex h-12 items-center gap-2 rounded-md border border-white/15 px-6 text-sm font-semibold text-white transition hover:border-white/35"
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
