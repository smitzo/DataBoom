"use client";

import { ArrowRight, Loader2, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { BrandLogo } from "@/components/brand";
import { register as registerRequest } from "@/lib/api";
import { loadSession, saveSession } from "@/lib/session";

export default function RegisterPage() {
  const router = useRouter();
  const [loginId, setLoginId] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
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
      const response = await registerRequest({
        login_id: loginId,
        email,
        name,
        password,
      });
      saveSession(response);
      router.push("/dashboard");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to create account");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#03050c] text-zinc-100">
      <div className="mx-auto flex min-h-screen max-w-6xl items-center px-6 py-10 sm:px-10">
        <section className="grid w-full gap-10 rounded-2xl border border-white/10 bg-white/[0.03] p-6 shadow-[0_30px_90px_rgba(0,0,0,0.35)] lg:grid-cols-[0.85fr_1.15fr] lg:p-10">
          <div>
            <BrandLogo
              size="lg"
              sublabel="Account setup"
              className="[--text-primary:#ffffff] [--text-faint:#71717a]"
            />
            <p className="mt-12 text-sm font-semibold uppercase tracking-[0.24em] text-emerald-200">
              Create workspace
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight text-white">
              Start with a login ID, then choose your data products.
            </h1>
            <p className="mt-5 text-base leading-7 text-zinc-400">
              Registration creates the application session. Product subscriptions,
              sources, runs, and LLM settings are managed inside the dashboard.
            </p>
          </div>

          <form className="space-y-4" onSubmit={submit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-semibold text-zinc-300">Login ID</span>
                <input
                  autoComplete="username"
                  className="mt-2 h-12 w-full rounded-lg border border-white/10 bg-black/35 px-4 text-sm text-white outline-none transition focus:border-cyan-300/60"
                  placeholder="team-alpha"
                  value={loginId}
                  onChange={(event) => setLoginId(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold text-zinc-300">Name</span>
                <input
                  autoComplete="name"
                  className="mt-2 h-12 w-full rounded-lg border border-white/10 bg-black/35 px-4 text-sm text-white outline-none transition focus:border-cyan-300/60"
                  placeholder="Team Alpha"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
            </div>

            <label className="block">
              <span className="text-sm font-semibold text-zinc-300">Email</span>
              <input
                autoComplete="email"
                className="mt-2 h-12 w-full rounded-lg border border-white/10 bg-black/35 px-4 text-sm text-white outline-none transition focus:border-cyan-300/60"
                placeholder="you@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-zinc-300">Password</span>
              <input
                autoComplete="new-password"
                className="mt-2 h-12 w-full rounded-lg border border-white/10 bg-black/35 px-4 text-sm text-white outline-none transition focus:border-cyan-300/60"
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
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              Create account
              <ArrowRight className="h-4 w-4" />
            </button>

            <p className="text-sm text-zinc-500">
              Already have access?{" "}
              <Link className="font-semibold text-cyan-200 hover:text-white" href="/login">
                Sign in
              </Link>
            </p>
          </form>
        </section>
      </div>
    </main>
  );
}
