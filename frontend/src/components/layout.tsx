import { Database, KeyRound, X } from "lucide-react";
import type { ReactNode } from "react";

import { PublicHeaderActions } from "@/components/public-session-actions";
import { navItems } from "@/data/workbench";

export function Announcement() {
  return (
    <div className="bg-gradient-to-r from-indigo-700 via-zinc-900 to-red-600">
      <div className="mx-auto flex h-10 max-w-[1680px] items-center justify-between gap-4 px-5 text-sm text-white sm:px-8 lg:px-12 xl:px-16">
        <div className="flex min-w-0 items-center gap-3">
          <span className="rounded-md bg-white/15 px-2 py-1 text-xs font-semibold">NEW</span>
          <span className="truncate font-medium">
            Generator-Boom now has Schema-Boom, Bank-O-Boom, and Health-Boom foundations.
          </span>
        </div>
        <X className="h-4 w-4 shrink-0 text-white/80" />
      </div>
    </div>
  );
}

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-black/95 backdrop-blur">
      <div className="mx-auto flex h-20 max-w-[1680px] items-center justify-between gap-5 px-5 sm:px-8 lg:px-12 xl:px-16">
        <a href="#platform" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-zinc-950 text-emerald-300 ring-1 ring-white/10">
            <Database className="h-5 w-5" />
          </span>
          <span className="text-sm font-semibold uppercase text-white">DataBoom</span>
        </a>

        <nav className="hidden items-center gap-2 lg:flex">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-zinc-400 transition hover:bg-white/5 hover:text-white"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <span className="inline-flex h-9 items-center gap-2 rounded-md border border-white/10 px-3 text-xs font-semibold uppercase text-zinc-400">
            <KeyRound className="h-3.5 w-3.5" />
            Local first
          </span>
          <PublicHeaderActions />
        </div>
      </div>
    </header>
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
    <section id={id} className="border-b border-white/10 bg-black">
      <div className="mx-auto max-w-[1680px] px-5 py-16 sm:px-8 lg:px-12 xl:px-16">
        <div className="grid gap-8 xl:grid-cols-[0.42fr_1fr]">
          <div>
            <p className="text-sm font-semibold uppercase text-zinc-500">{eyebrow}</p>
            <h2 className="mt-5 max-w-xl text-3xl font-semibold leading-tight text-white lg:text-5xl">
              {title}
            </h2>
            <p className="mt-5 max-w-xl text-base leading-7 text-zinc-400">{subtitle}</p>
          </div>
          <div>{children}</div>
        </div>
      </div>
    </section>
  );
}
