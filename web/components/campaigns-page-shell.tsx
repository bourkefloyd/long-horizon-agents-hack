import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

export function CampaignsPageShell({
  crumbs,
  title,
  description,
  actions,
  children,
}: {
  crumbs: { label: string; href?: string }[];
  title: ReactNode;
  description: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-7 sm:px-8 sm:py-10">
      <nav aria-label="Breadcrumb" className="mb-6">
        <ol className="flex flex-wrap items-center gap-1.5 text-sm text-muted-foreground">
          <li>
            <Link href="/" className="hover:text-foreground">
              Console
            </Link>
          </li>
          {crumbs.map((crumb) => (
            <li key={crumb.label} className="flex items-center gap-1.5">
              <ChevronRight className="size-3.5" aria-hidden="true" />
              {crumb.href ? (
                <Link href={crumb.href} className="hover:text-foreground">
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-foreground">{crumb.label}</span>
              )}
            </li>
          ))}
        </ol>
      </nav>
      <header className="mb-8 flex flex-col gap-5 border-b border-border/70 pb-7 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <h1 className="text-balance text-3xl font-semibold tracking-[-0.03em] sm:text-4xl">
            {title}
          </h1>
          <p className="mt-3 text-pretty text-sm leading-6 text-muted-foreground sm:text-base">
            {description}
          </p>
        </div>
        {actions ? (
          <div className="flex flex-col gap-3 sm:flex-row">{actions}</div>
        ) : null}
      </header>
      {children}
    </main>
  );
}
