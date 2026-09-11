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
    <main className="min-h-screen bg-[var(--page-bg)] text-[color:var(--text-primary)]">
      <div className="mx-auto flex min-h-screen max-w-6xl items-center px-6 py-10 sm:px-10">
        <section className="grid w-full gap-10 rounded-2xl border border-[color:var(--border)] bg-[var(--section-bg)] p-6 shadow-[0_30px_90px_var(--shadow-soft)] lg:grid-cols-[0.85fr_1.15fr] lg:p-10">
          <div>
            <BrandLogo size="lg" sublabel="Account setup" />
            <p className="mt-12 text-sm font-semibold uppercase tracking-[0.24em] text-[color:var(--accent-emerald)]">
              Create workspace
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight text-[color:var(--text-primary)]">
              Start with a login ID, then choose your data products.
            </h1>
            <p className="mt-5 text-base leading-7 text-[color:var(--text-muted)]">
              Registration creates the application session. Product subscriptions,
              sources, runs, and LLM settings are managed inside the dashboard.
            </p>
          </div>

          <form className="space-y-4" onSubmit={submit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-semibold text-[color:var(--text-secondary)]">Login ID</span>
                <input
                  autoComplete="username"
                  className="mt-2 h-12 w-full rounded-lg border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 text-sm text-[color:var(--text-primary)] outline-none transition placeholder:text-[color:var(--text-faint)] focus:border-cyan-300/60"
                  placeholder="team-alpha"
                  value={loginId}
                  onChange={(event) => setLoginId(event.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold text-[color:var(--text-secondary)]">Name</span>
                <input
                  autoComplete="name"
                  className="mt-2 h-12 w-full rounded-lg border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 text-sm text-[color:var(--text-primary)] outline-none transition placeholder:text-[color:var(--text-faint)] focus:border-cyan-300/60"
                  placeholder="Team Alpha"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
            </div>

            <label className="block">
              <span className="text-sm font-semibold text-[color:var(--text-secondary)]">Email</span>
              <input
                autoComplete="email"
                className="mt-2 h-12 w-full rounded-lg border border-[color:var(--border)] bg-[var(--surface-muted)] px-4 text-sm text-[color:var(--text-primary)] outline-none transition placeholder:text-[color:var(--text-faint)] focus:border-cyan-300/60"
                placeholder="you@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-[color:var(--text-secondary)]">Password</span>
              <input
                autoComplete="new-password"
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
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              Create account
              <ArrowRight className="h-4 w-4" />
            </button>

            <p className="text-sm text-[color:var(--text-muted)]">
              Already have access?{" "}
              <Link
                className="font-semibold text-[color:var(--accent-cyan)] hover:text-[color:var(--text-primary)]"
                href="/login"
              >
                Sign in
              </Link>
            </p>
          </form>
        </section>
      </div>
    </main>
  );
}
