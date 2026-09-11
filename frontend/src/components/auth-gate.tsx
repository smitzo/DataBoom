"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { getMe } from "@/lib/api";
import { clearSession, loadSession, type Session } from "@/lib/session";

export function AuthGate({ children }: { children: (session: Session) => ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const savedSession = loadSession();
    if (!savedSession) {
      router.replace("/login");
      return;
    }

    getMe(savedSession.token)
      .then((user) => {
        setSession({ token: savedSession.token, user });
      })
      .catch(() => {
        clearSession();
        router.replace("/login");
      })
      .finally(() => {
        setIsChecking(false);
      });
  }, [router]);

  if (isChecking || !session) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--page-bg)] text-[color:var(--text-primary)]">
        <div className="flex items-center gap-3 rounded-lg border border-[color:var(--border)] bg-[var(--surface-muted)] px-5 py-4 shadow-[0_18px_50px_var(--shadow-soft)]">
          <Loader2 className="h-5 w-5 animate-spin text-[color:var(--accent-cyan)]" />
          <span className="text-sm font-semibold text-[color:var(--text-secondary)]">
            Opening DataBoom console
          </span>
        </div>
      </main>
    );
  }

  return <AppShell session={session}>{children(session)}</AppShell>;
}
