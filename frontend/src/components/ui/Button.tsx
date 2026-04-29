import type { ButtonHTMLAttributes, PropsWithChildren } from "react";
import { cn } from "../../lib/cn";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-brand-teal text-white shadow-sm hover:bg-brand-cyan",
  secondary:
    "border border-brand-border bg-white text-brand-text shadow-sm hover:border-brand-teal/50 hover:bg-brand-surface",
  ghost: "bg-transparent text-brand-muted hover:bg-brand-surface hover:text-brand-text",
  danger: "bg-brand-danger text-white shadow-sm hover:bg-red-700",
};

export function Button({
  className,
  variant = "primary",
  children,
  ...props
}: PropsWithChildren<ButtonProps>) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[12px] px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60",
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
