"use client";

import { useEffect, useState } from "react";

import { loadSession } from "@/lib/session";

export function PublicHeaderActions() {
  const loggedIn = useLoggedIn();

  if (loggedIn === null) {
    return <div className="hidden h-11 w-48 md:block" />;
  }

  return (
    <div className="hidden items-center gap-3 md:flex">
      <a
        href={loggedIn ? "/dashboard" : "/login"}
        className="inline-flex h-12 items-center rounded-full bg-emerald-300 px-7 text-sm font-semibold text-slate-950 shadow-[0_14px_34px_rgba(16,185,129,0.18)] transition hover:bg-emerald-200"
      >
        {loggedIn ? "My dashboard" : "Log in"}
      </a>
    </div>
  );
}

function useLoggedIn() {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    setLoggedIn(Boolean(loadSession()));
  }, []);

  return loggedIn;
}
