import { cn } from "../../lib/cn";

interface BrandLogoProps {
  className?: string;
  imageClassName?: string;
  framed?: boolean;
  alt?: string;
}

export function BrandLogo({
  className,
  imageClassName,
  framed = true,
  alt = "Uganda Catholic Medical Bureau",
}: BrandLogoProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center justify-center",
        framed && "rounded-[24px] bg-white px-3 py-2 shadow-soft",
        className,
      )}
    >
      <img
        src="/ucmb-logo.gif"
        alt={alt}
        className={cn("block h-auto w-full max-w-full", imageClassName)}
      />
    </div>
  );
}
