import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        "w-full rounded-[14px] border border-brand-border bg-white px-3.5 py-2.5 text-sm text-brand-text shadow-sm outline-none transition-colors focus:border-brand-teal focus:ring-4 focus:ring-brand-cyan/20",
        className,
      )}
      {...props}
    />
  );
});
