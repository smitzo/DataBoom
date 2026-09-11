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
    <main className="min-h-screen bg-[#03050c] text-zinc-100">
      <div className="grid min-h-screen lg:grid-cols-[0.9fr_1.1fr]">
        <section className="flex items-center px-6 py-10 sm:px-10 lg:px-16">
          <div className="w-full max-w-md">
            <BrandLogo
              size="lg"
              sublabel="Secure workspace"
              className="[--text-primary:#ffffff] [--text-faint:#71717a]"
            />

            <p className="mt-12 text-sm font-semibold uppercase tracking-[0.24em] text-cyan-200">
              Product access
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight text-white sm:text-5xl">
              Sign in to your synthetic data workspace.
            </h1>
            <p className="mt-5 text-base leading-7 text-zinc-400">
              Use your login ID to manage workspaces, generate datasets, inspect previews,
              and export artifacts from active DataBoom products.
            </p>

            <form className="mt-10 space-y-4" onSubmit={submit}>
              <label className="block">
                <span className="text-sm font-semibold text-zinc-300">Login ID</span>
                <input
                  autoComplete="username"
                  className="mt-2 h-12 w-full rounded-lg border border-white/10 bg-white/[0.04] px-4 text-sm text-white outline-none transition focus:border-cyan-300/60"
                  placeholder="operator"
                  value={loginId}
                  onChange={(event) => setLoginId(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold text-zinc-300">Password</span>
                <input
                  autoComplete="current-password"
                  className="mt-2 h-12 w-full rounded-lg border border-white/10 bg-white/[0.04] px-4 text-sm text-white outline-none transition focus:border-cyan-300/60"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>

              {error ? (
                <p className="rounded-lg border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
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

            <p className="mt-6 text-sm text-zinc-500">
              New workspace?{" "}
              <Link className="font-semibold text-cyan-200 hover:text-white" href="/register">
                Create an account
              </Link>
            </p>
          </div>
        </section>

        <section className="hidden border-l border-white/10 bg-[radial-gradient(circle_at_20%_20%,rgba(45,212,191,0.16),transparent_34%),linear-gradient(135deg,#07101d,#03050c)] px-10 py-12 lg:block">
          <div className="flex h-full flex-col justify-between rounded-xl border border-white/10 bg-black/35 p-8 shadow-[0_30px_90px_rgba(0,0,0,0.35)]">
            <div>
              <div className="inline-flex h-11 items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 text-xs font-semibold uppercase text-emerald-100">
                <ShieldCheck className="h-4 w-4" />
                Engine-first platform
              </div>
              <h2 className="mt-10 max-w-2xl text-4xl font-semibold leading-tight text-white">
                Your data surface, run history, source connectors, and exports in one control plane.
              </h2>
            </div>

            <div className="grid gap-3">
              {[
                ["Connect", "Register a workspace and attach source metadata."],
                ["Generate", "Run Table-Boom or Docu-Boom with repeatable seeds."],
                ["Control", "Use platform LLM keys, your own key, or deterministic fallback."],
              ].map(([title, detail]) => (
                <div key={title} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-sm font-semibold text-white">{title}</p>
                  <p className="mt-1 text-sm leading-6 text-zinc-500">{detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
