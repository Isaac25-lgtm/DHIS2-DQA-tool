import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, children, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      className={cn(
        "w-full rounded-xl border border-brand-border bg-white px-3.5 py-2.5 text-sm text-brand-text shadow-sm outline-none transition focus:border-brand-teal focus:ring-4 focus:ring-brand-cyan/20",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
});

