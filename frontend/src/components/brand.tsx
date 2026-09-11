import Link from "next/link";

import { brandAssets } from "@/assets/brand";

type BrandSize = "sm" | "md" | "lg";

const brandSizes: Record<
  BrandSize,
  {
    mark: string;
    image: string;
    title: string;
    subtitle: string;
  }
> = {
  sm: {
    mark: "h-11 w-11 rounded-xl",
    image: "h-10 w-10",
    title: "text-base",
    subtitle: "text-xs",
  },
  md: {
    mark: "h-14 w-14 rounded-2xl",
    image: "h-12 w-12",
    title: "text-xl",
    subtitle: "text-sm",
  },
  lg: {
    mark: "h-16 w-16 rounded-2xl",
    image: "h-14 w-14",
    title: "text-2xl",
    subtitle: "text-sm",
  },
};

export function BrandMark({ size = "md" }: { size?: BrandSize }) {
  const classes = brandSizes[size];

  return (
    <span
      className={`relative grid shrink-0 place-items-center overflow-hidden transition duration-300 group-hover:-translate-y-0.5 ${classes.mark}`}
      aria-hidden="true"
    >
      <img
        alt=""
        className={`${classes.image} drop-shadow-[0_14px_32px_rgba(20,184,166,0.24)]`}
        src={brandAssets.mark}
      />
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
          className={`block font-semibold leading-none text-[color:var(--text-primary)] ${classes.title}`}
        >
          Data<span className="text-[color:var(--brand-accent)]">Boom</span>
        </span>
        {sublabel ? (
          <span className={`mt-1 block text-[color:var(--text-faint)] ${classes.subtitle}`}>
            {sublabel}
          </span>
        ) : null}
      </span>
    </>
  );

  const wrapperClassName = `group flex items-center gap-4 ${className}`;

  if (!href) {
    return <div className={wrapperClassName}>{content}</div>;
  }

  return (
    <Link href={href} className={wrapperClassName} aria-label="DataBoom home">
      {content}
    </Link>
  );
}
