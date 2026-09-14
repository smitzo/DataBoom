"use client";

import { BrainCircuit, KeyRound, Loader2, PackageCheck, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { PageHeader } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import type { LlmPolicy } from "@/lib/api";
import { getLlmPolicy, resolveLlmPolicy } from "@/lib/api";
import type { Session } from "@/lib/session";
import { getSessionLlmKey, setSessionLlmKey } from "@/lib/llm-key";

export default function SettingsPage() {
  return (
    <AuthGate>
      {(session) => <SettingsContent session={session} />}
    </AuthGate>
  );
}

function SettingsContent({ session }: { session: Session }) {
  const [policy, setPolicy] = useState<LlmPolicy | null>(null);
  const [userApiKey, setUserApiKey] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isResolving, setIsResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUserApiKey(getSessionLlmKey());
    getLlmPolicy(session.token)
      .then(setPolicy)
      .catch((caughtError) => {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load settings");
      })
      .finally(() => setIsLoading(false));
  }, [session.token]);

  const resolvePolicy = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsResolving(true);

    try {
      const nextPolicy = await resolveLlmPolicy(session.token, userApiKey);
      setPolicy(nextPolicy);
      setSessionLlmKey(userApiKey);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to resolve key policy");
    } finally {
      setIsResolving(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Settings"
        title="Workspace controls"
        description="Manage account access, product subscriptions, and optional LLM provider behavior for planning-assisted workflows."
      />

      {error ? (
        <p className="mb-6 rounded-lg border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
          {error}
        </p>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-xl border border-white/10 bg-white/[0.035] p-5">
          <div className="flex items-start gap-4">
            <div className="grid h-12 w-12 place-items-center rounded-xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-100">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold uppercase text-zinc-500">Signed in as</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">{session.user.name}</h2>
              <p className="mt-1 text-sm text-zinc-500">{session.user.email}</p>
            </div>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            <Link
              className="rounded-lg border border-white/10 bg-black/25 p-4 transition hover:border-emerald-300/35 hover:bg-white/[0.05]"
              href="/settings/subscriptions"
            >
              <PackageCheck className="h-5 w-5 text-emerald-200" />
              <p className="mt-4 font-semibold text-white">Subscriptions</p>
              <p className="mt-2 text-sm leading-6 text-zinc-500">
                Review active DataBoom products and open product workspaces.
              </p>
            </Link>
            <div className="rounded-lg border border-white/10 bg-black/25 p-4">
              <KeyRound className="h-5 w-5 text-cyan-200" />
              <p className="mt-4 font-semibold text-white">Session security</p>
              <p className="mt-2 text-sm leading-6 text-zinc-500">
                Sessions use opaque bearer tokens and server-side password hashes.
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.035] p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase text-cyan-200">LLM provider</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Planning assistant policy</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
                The engine always works deterministically. LLM calls are optional and only used for
                future schema planning, field suggestions, and explanations.
              </p>
            </div>
            <ModeBadge policy={policy} isLoading={isLoading} />
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <PolicyTile label="Model" value={policy?.default_model ?? "Loading"} />
            <PolicyTile label="Token limit" value={policy ? policy.token_limit.toLocaleString() : "Loading"} />
            <PolicyTile label="Platform key" value={policy?.platform_key_configured ? "Configured" : "Fallback"} />
          </div>

          <form className="mt-6 rounded-lg border border-white/10 bg-black/25 p-4" onSubmit={resolvePolicy}>
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <BrainCircuit className="h-4 w-4 text-cyan-200" />
              Use my API key for this request
            </div>
            <p className="mt-2 text-sm leading-6 text-zinc-500">
              The key is kept only in this browser tab and sent directly with planning requests.
              DataBoom does not persist it in the backend.
            </p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <input
                className="h-11 flex-1 rounded-lg border border-white/10 bg-white/[0.04] px-4 text-sm text-white outline-none transition focus:border-cyan-300/60"
                placeholder="Paste key only when you want to use BYOK"
                type="password"
                value={userApiKey}
                onChange={(event) => setUserApiKey(event.target.value)}
              />
              <button
                className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-emerald-300 px-4 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isResolving}
              >
                {isResolving ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                Resolve policy
              </button>
            </div>
          </form>
        </section>
      </div>
    </>
  );
}

function ModeBadge({ policy, isLoading }: { policy: LlmPolicy | null; isLoading: boolean }) {
  if (isLoading || !policy) {
    return (
      <span className="inline-flex h-10 items-center rounded-full border border-white/10 px-4 text-xs font-semibold uppercase text-zinc-400">
        Loading
      </span>
    );
  }

  const labels: Record<LlmPolicy["active_mode"], string> = {
    deterministic_fallback: "Deterministic fallback",
    platform_key: "Platform key",
    user_key: "User key",
  };

  return (
    <span className="inline-flex h-10 items-center rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 text-xs font-semibold uppercase text-emerald-100">
      {labels[policy.active_mode]}
    </span>
  );
}

function PolicyTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/25 p-4">
      <p className="text-xs font-semibold uppercase text-zinc-500">{label}</p>
      <p className="mt-3 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
