import { Database, KeyRound, X } from "lucide-react";
import type { ReactNode } from "react";

import { PublicHeaderActions } from "@/components/public-session-actions";
import { ThemeToggle } from "@/components/theme-toggle";
import { navItems } from "@/data/workbench";

export function Announcement() {
  return (
    <div className="bg-gradient-to-r from-emerald-600 via-slate-950 to-sky-600">
      <div className="mx-auto flex h-10 max-w-[1680px] items-center justify-between gap-4 px-5 text-sm text-white sm:px-8 lg:px-12 xl:px-16">
        <div className="flex min-w-0 items-center gap-3">
          <span className="rounded-md bg-white/15 px-2 py-1 text-xs font-semibold">NEW</span>
          <span className="truncate font-medium">
            Table-Boom and Docu-Boom are active; Graph-Boom and Masker-Boom are next.
          </span>
        </div>
        <X className="h-4 w-4 shrink-0 text-white/80" />
      </div>
    </div>
  );
}

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-[color:var(--border)] bg-[color:var(--header-bg)] backdrop-blur">
      <div className="mx-auto flex h-20 max-w-[1680px] items-center justify-between gap-5 px-5 sm:px-8 lg:px-12 xl:px-16">
        <a href="/" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20">
            <Database className="h-5 w-5" />
          </span>
          <span className="text-sm font-semibold uppercase text-[color:var(--text-primary)]">
            DataBoom
          </span>
        </a>

        <nav className="hidden items-center gap-2 lg:flex">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-[color:var(--text-muted)] transition hover:bg-[var(--surface)] hover:text-[color:var(--text-primary)]"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <ThemeToggle />
          <span className="inline-flex h-9 items-center gap-2 rounded-md border border-[color:var(--border)] px-3 text-xs font-semibold uppercase text-[color:var(--text-muted)]">
            <KeyRound className="h-3.5 w-3.5" />
            Local first
          </span>
          <PublicHeaderActions />
        </div>
      </div>
    </header>
  );
}

export function PublicShell({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-screen bg-[var(--page-bg)] text-[color:var(--text-primary)]">
      <Announcement />
      <Header />
      {children}
      <PublicFooter />
    </main>
  );
}

export function Section({
  id,
  eyebrow,
  title,
  subtitle,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="border-b border-[color:var(--border)] bg-[var(--section-bg)]">
      <div className="mx-auto max-w-[1680px] px-5 py-16 sm:px-8 lg:px-12 xl:px-16">
        <div className="grid gap-8 xl:grid-cols-[0.42fr_1fr]">
          <div>
            <p className="text-sm font-semibold uppercase text-[color:var(--text-faint)]">
              {eyebrow}
            </p>
            <h2 className="mt-5 max-w-xl text-3xl font-semibold leading-tight text-[color:var(--text-primary)] lg:text-5xl">
              {title}
            </h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-[color:var(--text-muted)]">
              {subtitle}
            </p>
          </div>
          <div>{children}</div>
        </div>
      </div>
    </section>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t border-[color:var(--border)] bg-[var(--page-bg)]">
      <div className="mx-auto grid max-w-[1680px] gap-8 px-5 py-12 sm:px-8 lg:grid-cols-[1fr_1.4fr] lg:px-12 xl:px-16">
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20">
              <Database className="h-5 w-5" />
            </span>
            <span className="text-sm font-semibold uppercase text-[color:var(--text-primary)]">
              DataBoom
            </span>
          </div>
          <p className="mt-4 max-w-md text-sm leading-6 text-[color:var(--text-muted)]">
            Synthetic relational and document data generation today, graph and masking workflows next.
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase text-[color:var(--text-faint)]">Sitemap</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: "Home", href: "/" },
              { label: "Products", href: "/products" },
              { label: "Demos", href: "/demos" },
              { label: "Roadmap", href: "/roadmap" },
              { label: "Contact", href: "/contact" },
              { label: "My dashboard", href: "/dashboard" },
            ].map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="rounded-md border border-[color:var(--border)] bg-[var(--surface)] px-3 py-2 text-sm font-semibold text-[color:var(--text-secondary)] transition hover:bg-[var(--surface-strong)] hover:text-[color:var(--text-primary)]"
              >
                {item.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
