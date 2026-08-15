import { KeyRound, X } from "lucide-react";
import type { ReactNode } from "react";

import { BrandLogo } from "@/components/brand";
import { PublicHeaderActions } from "@/components/public-session-actions";
import { ThemeToggle } from "@/components/theme-toggle";
import { navItems } from "@/data/workbench";

export function Announcement() {
  return (
    <div className="relative overflow-hidden bg-gradient-to-r from-emerald-500 via-cyan-950 to-sky-600">
      <div className="absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-white/15 to-transparent opacity-60 motion-safe:animate-pulse" />
      <div className="relative mx-auto flex h-12 max-w-[1760px] items-center justify-between gap-4 px-5 text-sm text-white sm:px-8 lg:px-12 xl:px-16">
        <div className="flex min-w-0 items-center gap-3">
          <span className="rounded-md bg-white/15 px-2.5 py-1 text-xs font-semibold">NEW</span>
          <span className="truncate font-semibold">
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
    <header className="sticky top-0 z-30 border-b border-[color:var(--border)] bg-[color:var(--header-bg)] shadow-[0_18px_60px_rgba(0,0,0,0.24)] backdrop-blur-xl">
      <div className="mx-auto flex h-28 max-w-[1760px] items-center justify-between gap-6 px-5 sm:px-8 lg:px-12 xl:px-16">
        <BrandLogo size="lg" sublabel="Synthetic data engine" />

        <nav className="hidden items-center gap-1 lg:flex xl:gap-2">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded-md px-4 py-3 text-[15px] font-medium text-[color:var(--text-muted)] transition hover:bg-[var(--surface)] hover:text-[color:var(--text-primary)]"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <ThemeToggle />
          <span className="inline-flex h-11 items-center gap-2 rounded-md border border-[color:var(--border)] bg-[var(--surface)] px-4 text-sm font-medium text-[color:var(--text-muted)]">
            <KeyRound className="h-4 w-4" />
            Local-first
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
      <div className="mx-auto max-w-[1760px] px-5 py-20 sm:px-8 lg:px-12 xl:px-16">
        <div className="grid gap-8 xl:grid-cols-[0.42fr_1fr]">
          <div>
            <p className="text-sm font-semibold uppercase text-[color:var(--text-faint)]">
              {eyebrow}
            </p>
            <h2 className="mt-5 max-w-xl text-3xl font-medium leading-tight text-[color:var(--text-primary)] lg:text-5xl">
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
      <div className="mx-auto grid max-w-[1760px] gap-8 px-5 py-12 sm:px-8 lg:grid-cols-[1fr_1.4fr] lg:px-12 xl:px-16">
        <div>
          <BrandLogo size="md" sublabel="Table-Boom, Docu-Boom, Graph-Boom, Masker-Boom" />
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
              { label: "About", href: "/about" },
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
