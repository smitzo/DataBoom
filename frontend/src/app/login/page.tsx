"use client";

import { ArrowRight, KeyRound, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { BrandLogo } from "@/components/brand";
import { login as loginRequest } from "@/lib/api";
import { loadSession, saveSession } from "@/lib/session";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("demo");
  const [password, setPassword] = useState("demo");
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
      const response = await loginRequest(email, password);
      saveSession(response);
      router.push("/dashboard");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to login");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <div className="grid min-h-screen lg:grid-cols-[0.95fr_1.05fr]">
        <section className="flex items-center px-6 py-10 sm:px-10 lg:px-16">
          <div className="w-full max-w-md">
            <BrandLogo size="lg" sublabel="Product workspace" className="[--text-primary:#ffffff] [--text-faint:#71717a]" />

            <h1 className="mt-12 text-4xl font-semibold leading-tight text-white sm:text-5xl">
              Login to subscribe, generate, preview, and download synthetic data.
            </h1>
            <p className="mt-5 text-base leading-7 text-zinc-400">
              Use the sample credentials below for the local full-stack flow.
            </p>

            <form className="mt-10 space-y-4" onSubmit={submit}>
              <label className="block">
                <span className="text-sm font-semibold text-zinc-300">Email</span>
                <input
                  className="mt-2 h-12 w-full rounded-md border border-white/10 bg-white/[0.04] px-4 text-sm text-white outline-none transition focus:border-cyan-300/50"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold text-zinc-300">Password</span>
                <input
                  className="mt-2 h-12 w-full rounded-md border border-white/10 bg-white/[0.04] px-4 text-sm text-white outline-none transition focus:border-cyan-300/50"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>

              {error ? (
                <p className="rounded-md border border-red-300/25 bg-red-300/10 px-4 py-3 text-sm text-red-100">
                  {error}
                </p>
              ) : null}

              <button
                className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-md bg-white text-sm font-semibold text-zinc-950 transition hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <KeyRound className="h-4 w-4" />
                )}
                Login as demo
                <ArrowRight className="h-4 w-4" />
              </button>
            </form>
          </div>
        </section>

        <section className="hidden border-l border-white/10 bg-zinc-950 px-10 py-12 lg:block">
          <div className="flex h-full flex-col justify-between rounded-lg border border-white/10 bg-black/40 p-8">
            <div>
              <p className="text-sm font-semibold uppercase text-cyan-300">Demo workflow</p>
              <div className="mt-8 grid gap-4">
                {[
                  "Authenticate demo user",
                  "Subscribe to Table-Boom or Docu-Boom",
                  "Generate records through FastAPI",
                  "Preview table rows or JSON documents",
                  "Download generated artifacts and validation reports",
                ].map((step, index) => (
                  <div
                    key={step}
                    className="flex items-center gap-4 rounded-md border border-white/10 bg-white/[0.03] p-4"
                  >
                    <span className="flex h-9 w-9 items-center justify-center rounded-md bg-cyan-300/10 text-sm font-semibold text-cyan-200">
                      {index + 1}
                    </span>
                    <span className="text-sm font-medium text-zinc-300">{step}</span>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-sm leading-6 text-zinc-500">
              Demo credentials: email <span className="text-white">demo</span>, password{" "}
              <span className="text-white">demo</span>.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
