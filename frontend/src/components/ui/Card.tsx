import type { HTMLAttributes, PropsWithChildren } from "react";
import { cn } from "../../lib/cn";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
}

export function Card({
  className,
  title,
  subtitle,
  children,
  ...props
}: PropsWithChildren<CardProps>) {
  return (
    <section
      className={cn(
        "rounded-[22px] border border-brand-border bg-white p-5 shadow-soft",
        className,
      )}
      {...props}
    >
      {(title || subtitle) && (
        <header className="mb-5 border-b border-brand-border/70 pb-4">
          {title ? <h2 className="font-display text-xl font-semibold text-brand-text">{title}</h2> : null}
          {subtitle ? <p className="mt-1 text-sm text-brand-muted">{subtitle}</p> : null}
        </header>
      )}
      {children}
    </section>
  );
}
