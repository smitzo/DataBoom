"use client";

import { ChevronRight, Home } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const routeLabels: Record<string, string> = {
  about: "About",
  contact: "Contact",
  dashboard: "Dashboard",
  demos: "Demos",
  login: "Login",
  products: "Products",
  register: "Register",
  roadmap: "Roadmap",
  runs: "Runs",
  settings: "Settings",
  subscriptions: "Subscriptions",
};

export function Breadcrumbs({
  className = "",
  tone = "dark",
}: {
  className?: string;
  tone?: "dark" | "light";
}) {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  const items = [
    { href: "/", label: "Home" },
    ...segments.map((segment, index) => {
      const href = `/${segments.slice(0, index + 1).join("/")}`;
      return { href, label: routeLabels[segment] ?? humanizeSegment(segment) };
    }),
  ];

  if (pathname === "/") {
    return null;
  }

  const muted = tone === "dark" ? "text-zinc-500" : "text-[color:var(--text-faint)]";
  const active = tone === "dark" ? "text-zinc-200" : "text-[color:var(--text-secondary)]";
  const hover = tone === "dark" ? "hover:text-cyan-100" : "hover:text-[color:var(--text-primary)]";

  return (
    <nav
      aria-label="Breadcrumb"
      className={`flex min-w-0 items-center gap-1.5 text-xs font-semibold ${muted} ${className}`}
    >
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={item.href} className="flex min-w-0 items-center gap-1.5">
            {index > 0 ? <ChevronRight className="h-3.5 w-3.5 shrink-0 opacity-60" /> : null}
            {isLast ? (
              <span className={`truncate ${active}`}>{item.label}</span>
            ) : (
              <Link className={`inline-flex min-w-0 items-center gap-1 truncate transition ${hover}`} href={item.href}>
                {index === 0 ? <Home className="h-3.5 w-3.5 shrink-0" /> : null}
                <span className="truncate">{item.label}</span>
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export function PublicBreadcrumbBand() {
  const pathname = usePathname();

  if (pathname === "/") {
    return null;
  }

  return (
    <div className="border-b border-[color:var(--border)] bg-[var(--page-bg)]">
      <div className="mx-auto max-w-[1760px] px-5 py-3 sm:px-8 lg:px-12 xl:px-16">
        <Breadcrumbs tone="light" />
      </div>
    </div>
  );
}

function humanizeSegment(segment: string) {
  return segment
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
