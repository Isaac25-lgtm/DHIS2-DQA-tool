import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "min-h-28 w-full rounded-[16px] border border-brand-border bg-white px-3.5 py-2.5 text-sm text-brand-text shadow-sm outline-none transition-colors focus:border-brand-teal focus:ring-4 focus:ring-brand-cyan/20",
        className,
      )}
      {...props}
    />
  );
});
