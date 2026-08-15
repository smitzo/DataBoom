"use client";

import {
  BarChart3,
  LayoutDashboard,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  ShieldCheck,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useState } from "react";

import { BrandLogo, BrandMark } from "@/components/brand";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { clearSession, type Session } from "@/lib/session";

const navItems = [
  {
    href: "/dashboard",
    label: "Workspace",
    description: "Generate and preview data",
    icon: LayoutDashboard,
  },
  { href: "/runs", label: "Runs", description: "History and artifacts", icon: BarChart3 },
  {
    href: "/settings/subscriptions",
    label: "Subscriptions",
    description: "Product access",
    icon: Settings,
  },
];

export function AppShell({ session, children }: { session: Session; children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [isNavCollapsed, setIsNavCollapsed] = useState(true);

  const logout = () => {
    clearSession();
    router.push("/login");
  };

  return (
    <main className="min-h-screen bg-[#050714] text-zinc-100">
      <aside
        className={`fixed inset-y-0 left-0 z-40 hidden border-r border-white/10 bg-[#080b16]/95 py-5 shadow-[18px_0_60px_rgba(0,0,0,0.22)] transition-[width,padding] duration-300 lg:block ${
          isNavCollapsed ? "w-20 px-3" : "w-64 px-4"
        }`}
      >
        <div
          className={
            isNavCollapsed
              ? "grid justify-items-center gap-3"
              : "flex items-center justify-between gap-3"
          }
        >
          {isNavCollapsed ? <BrandMark size="sm" /> : <BrandLogo size="md" sublabel="Product console" />}
          <button
            aria-label={isNavCollapsed ? "Expand navigation" : "Collapse navigation"}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-white/10 text-zinc-400 transition hover:border-cyan-300/30 hover:text-cyan-100"
            onClick={() => setIsNavCollapsed((current) => !current)}
            title={isNavCollapsed ? "Expand navigation" : "Collapse navigation"}
          >
            {isNavCollapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>
        </div>

        <nav className="mt-8 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={item.label}
                className={`flex rounded-xl border text-sm transition ${
                  isNavCollapsed ? "h-11 items-center justify-center px-0 py-0" : "items-start gap-3 px-3 py-2.5"
                } ${
                  active
                    ? "border-cyan-300/25 bg-cyan-300/10 text-cyan-100"
                    : "border-transparent text-zinc-500 hover:border-white/10 hover:bg-white/[0.04] hover:text-white"
                }`}
              >
                <Icon className={`${isNavCollapsed ? "h-4 w-4" : "mt-0.5 h-4 w-4"} shrink-0`} />
                {isNavCollapsed ? null : (
                  <span>
                    <span className="block font-semibold">{item.label}</span>
                    <span className="mt-1 block text-xs text-zinc-600">{item.description}</span>
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div
          className={`absolute bottom-5 rounded-xl border border-white/10 bg-white/[0.03] ${
            isNavCollapsed ? "left-3 right-3 p-2" : "left-4 right-4 p-4"
          }`}
        >
          {isNavCollapsed ? (
            <div className="grid place-items-center gap-2">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-cyan-300/10 text-xs font-semibold text-cyan-100">
                {session.user.name
                  .split(" ")
                  .map((part) => part[0])
                  .join("")
                  .slice(0, 2)}
              </span>
            </div>
          ) : (
            <>
              <p className="text-xs font-semibold uppercase text-zinc-500">Signed in</p>
              <p className="mt-2 text-sm font-semibold text-white">{session.user.name}</p>
              <p className="text-xs text-zinc-500">{session.user.email}</p>
            </>
          )}
          <button
            className={`inline-flex h-9 w-full items-center justify-center gap-2 rounded-md border border-white/10 text-sm font-semibold text-zinc-300 transition hover:border-red-300/40 hover:text-red-200 ${
              isNavCollapsed ? "mt-2" : "mt-4"
            }`}
            onClick={logout}
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
            {isNavCollapsed ? null : "Logout"}
          </button>
        </div>
      </aside>

      <div className={isNavCollapsed ? "lg:pl-20" : "lg:pl-64"}>
        <header className="sticky top-0 z-30 border-b border-white/10 bg-[#050714]/85 backdrop-blur-xl">
          <div className="flex min-h-16 items-center justify-between gap-4 px-5 sm:px-8">
            <BrandLogo
              size="sm"
              sublabel="Console"
              className="lg:hidden [--text-primary:#ffffff] [--text-faint:#71717a]"
            />
            <div className="hidden lg:block">
              <Breadcrumbs className="mb-1" />
              <p className="text-sm font-semibold text-zinc-200">Data operations workspace</p>
              <p className="text-xs text-zinc-500">Generate, validate, preview, export.</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="hidden h-10 items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 text-xs font-semibold uppercase text-emerald-100 md:inline-flex">
                <ShieldCheck className="h-3.5 w-3.5" />
                Demo workspace
              </span>
              <span className="hidden rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm font-semibold text-zinc-200 xl:inline-flex">
                {session.user.name}
              </span>
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

        <div className="mx-auto max-w-none px-4 py-5 sm:px-6">{children}</div>
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
        <h1 className="mt-3 text-4xl font-medium leading-tight text-white lg:text-5xl">{title}</h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-zinc-400">{description}</p>
      </div>
      {action}
    </div>
  );
}
