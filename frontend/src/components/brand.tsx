import { Database, Sparkles } from "lucide-react";
import Link from "next/link";

type BrandSize = "sm" | "md" | "lg";

const brandSizes: Record<
  BrandSize,
  {
    mark: string;
    icon: string;
    spark: string;
    title: string;
    subtitle: string;
  }
> = {
  sm: {
    mark: "h-10 w-10 rounded-lg",
    icon: "h-5 w-5",
    spark: "h-3 w-3 right-1.5 top-1.5",
    title: "text-sm",
    subtitle: "text-xs",
  },
  md: {
    mark: "h-12 w-12 rounded-xl",
    icon: "h-6 w-6",
    spark: "h-3.5 w-3.5 right-2 top-2",
    title: "text-lg",
    subtitle: "text-xs",
  },
  lg: {
    mark: "h-14 w-14 rounded-xl",
    icon: "h-7 w-7",
    spark: "h-4 w-4 right-2 top-2",
    title: "text-xl",
    subtitle: "text-sm",
  },
};

export function BrandMark({ size = "md" }: { size?: BrandSize }) {
  const classes = brandSizes[size];

  return (
    <span
      className={`relative grid shrink-0 place-items-center overflow-hidden border border-emerald-300/35 bg-emerald-300/10 text-emerald-200 shadow-[0_0_30px_rgba(45,212,191,0.18)] transition duration-300 group-hover:scale-105 group-hover:border-cyan-300/50 ${classes.mark}`}
      aria-hidden="true"
    >
      <span className="absolute inset-0 bg-[radial-gradient(circle_at_76%_18%,rgba(56,189,248,0.35),transparent_30%)]" />
      <Database className={`relative z-10 ${classes.icon}`} />
      <Sparkles className={`absolute z-20 text-cyan-200 motion-safe:animate-pulse ${classes.spark}`} />
      <span className="absolute bottom-2 left-2 right-2 h-1 rounded-full bg-gradient-to-r from-emerald-300 via-cyan-300 to-sky-300 opacity-80" />
    </span>
  );
}

export function BrandLogo({
  href = "/",
  size = "md",
  sublabel,
  className = "",
}: {
  href?: string | null;
  size?: BrandSize;
  sublabel?: string;
  className?: string;
}) {
  const classes = brandSizes[size];
  const content = (
    <>
      <BrandMark size={size} />
      <span className="min-w-0">
        <span
          className={`block font-semibold uppercase leading-none text-[color:var(--text-primary)] ${classes.title}`}
        >
          Data<span className="text-emerald-300">Boom</span>
        </span>
        {sublabel ? (
          <span className={`mt-1 block text-[color:var(--text-faint)] ${classes.subtitle}`}>
            {sublabel}
          </span>
        ) : null}
      </span>
    </>
  );

  const wrapperClassName = `group flex items-center gap-3 ${className}`;

  if (!href) {
    return <div className={wrapperClassName}>{content}</div>;
  }

  return (
    <Link href={href} className={wrapperClassName} aria-label="DataBoom home">
      {content}
    </Link>
  );
}
