"use client";

import { ArrowRight, KeyRound, Loader2, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { BrandLogo } from "@/components/brand";
import { login as loginRequest } from "@/lib/api";
import { loadSession, saveSession } from "@/lib/session";

export default function LoginPage() {
  const router = useRouter();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loadSession()) {
      router.replace("/dashboard");
    }
  }, [router]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await loginRequest(loginId, password);
      saveSession(response);
      router.push("/dashboard");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to sign in");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-[var(--page-bg)] text-[color:var(--text-primary)]">
      <div className="grid min-h-screen lg:grid-cols-[0.9fr_1.1fr]">
        <section className="flex items-center px-6 py-10 sm:px-10 lg:px-16">
          <div className="w-full max-w-md">
            <BrandLogo size="lg" sublabel="Secure workspace" />

            <p className="mt-12 text-sm font-semibold uppercase tracking-[0.24em] text-[color:var(--accent-cyan)]">
              Product access
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight text-[color:var(--text-primary)] sm:text-5xl">
              Sign in to your synthetic data workspace.
            </h1>
            <p className="mt-5 text-base leading-7 text-[color:var(--text-muted)]">
              Use your login ID to manage workspaces, generate datasets, inspect previews,
              and export artifacts from active DataBoom products.
            </p>

            <form className="mt-10 space-y-4" onSubmit={submit}>
              <label className="block">
                <span className="text-sm font-semibold text-[color:var(--text-secondary)]">Login ID</span>
                <input
                  autoComplete="username"
                  className="mt-2 h-12 w-full rounded-lg border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 text-sm text-[color:var(--text-primary)] outline-none transition placeholder:text-[color:var(--text-faint)] focus:border-cyan-300/60"
                  placeholder="operator"
                  value={loginId}
                  onChange={(event) => setLoginId(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold text-[color:var(--text-secondary)]">Password</span>
                <input
                  autoComplete="current-password"
                  className="mt-2 h-12 w-full rounded-lg border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 text-sm text-[color:var(--text-primary)] outline-none transition focus:border-cyan-300/60"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>

              {error ? (
                <p className="rounded-lg border border-[color:var(--danger-border)] bg-[var(--danger-bg)] px-4 py-3 text-sm text-[color:var(--danger-text)]">
                  {error}
                </p>
              ) : null}

              <button
                className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-emerald-300 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <KeyRound className="h-4 w-4" />
                )}
                Sign in
                <ArrowRight className="h-4 w-4" />
              </button>
            </form>

            <p className="mt-6 text-sm text-[color:var(--text-muted)]">
              New workspace?{" "}
              <Link
                className="font-semibold text-[color:var(--accent-cyan)] hover:text-[color:var(--text-primary)]"
                href="/register"
              >
                Create an account
              </Link>
            </p>
          </div>
        </section>

        <section className="hero-shell hidden border-l border-[color:var(--border)] px-10 py-12 lg:block">
          <div className="flex h-full flex-col justify-between rounded-xl border border-[color:var(--hero-border)] bg-[var(--hero-surface)] p-8 shadow-[0_30px_90px_var(--shadow-soft)]">
            <div>
              <div className="inline-flex h-11 items-center gap-2 rounded-full border border-emerald-300/25 bg-emerald-300/10 px-4 text-xs font-semibold uppercase text-[color:var(--accent-emerald)]">
                <ShieldCheck className="h-4 w-4" />
                Engine-first platform
              </div>
              <h2 className="mt-10 max-w-2xl text-4xl font-semibold leading-tight text-[color:var(--hero-text-primary)]">
                Your data surface, run history, source connectors, and exports in one control plane.
              </h2>
            </div>

            <div className="grid gap-3">
              {[
                ["Connect", "Register a workspace and attach source metadata."],
                ["Generate", "Run Table-Boom or Docu-Boom with repeatable seeds."],
                ["Control", "Use platform LLM keys, your own key, or deterministic fallback."],
              ].map(([title, detail]) => (
                <div
                  key={title}
                  className="rounded-lg border border-[color:var(--hero-border)] bg-[var(--hero-surface)] p-4"
                >
                  <p className="text-sm font-semibold text-[color:var(--hero-text-primary)]">{title}</p>
                  <p className="mt-1 text-sm leading-6 text-[color:var(--hero-text-muted)]">{detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
