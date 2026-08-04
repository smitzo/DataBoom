"use client";

import {
  BarChart3,
  Database,
  LayoutDashboard,
  LogOut,
  PackageCheck,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { clearSession, type Session } from "@/lib/session";

const navItems = [
  { href: "/dashboard", label: "Relational", icon: LayoutDashboard },
  { href: "/products", label: "Products", icon: PackageCheck },
  { href: "/runs", label: "Runs", icon: BarChart3 },
  { href: "/settings/subscriptions", label: "Settings", icon: Settings },
];

export function AppShell({ session, children }: { session: Session; children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const logout = () => {
    clearSession();
    router.push("/login");
  };

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-72 border-r border-white/10 bg-zinc-950/95 px-5 py-6 lg:block">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-md border border-emerald-300/25 bg-emerald-300/10 text-emerald-200">
            <Database className="h-5 w-5" />
          </span>
          <span>
            <span className="block text-sm font-semibold uppercase tracking-wide text-white">
              DataBoom
            </span>
            <span className="text-xs text-zinc-500">Relational console</span>
          </span>
        </Link>

        <nav className="mt-10 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition ${
                  active
                    ? "bg-cyan-300/10 text-cyan-100 ring-1 ring-cyan-300/25"
                    : "text-zinc-500 hover:bg-white/[0.04] hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-6 left-5 right-5 rounded-lg border border-white/10 bg-white/[0.03] p-4">
          <p className="text-xs font-semibold uppercase text-zinc-500">Signed in</p>
          <p className="mt-2 text-sm font-semibold text-white">{session.user.name}</p>
          <p className="text-xs text-zinc-500">{session.user.email}</p>
          <button
            className="mt-4 inline-flex h-9 w-full items-center justify-center gap-2 rounded-md border border-white/10 text-sm font-semibold text-zinc-300 transition hover:border-red-300/40 hover:text-red-200"
            onClick={logout}
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-30 border-b border-white/10 bg-black/85 backdrop-blur">
          <div className="flex min-h-16 items-center justify-between gap-4 px-5 sm:px-8">
            <Link href="/" className="flex items-center gap-3 lg:hidden">
              <Database className="h-5 w-5 text-emerald-200" />
              <span className="text-sm font-semibold uppercase text-white">DataBoom</span>
            </Link>
            <div className="hidden lg:block">
              <p className="text-xs font-semibold uppercase text-zinc-600">Local full-stack MVP</p>
              <p className="text-sm text-zinc-400">
                DataBoom Relational workspace.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md border border-white/10 px-3 py-2 text-xs font-semibold text-zinc-300 lg:hidden"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-none px-4 py-4 sm:px-6">{children}</div>
      </div>
    </main>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <p className="text-sm font-semibold uppercase text-cyan-300">{eyebrow}</p>
        <h1 className="mt-3 text-4xl font-semibold leading-tight text-white lg:text-5xl">{title}</h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-zinc-400">{description}</p>
      </div>
      {action}
    </div>
  );
}
