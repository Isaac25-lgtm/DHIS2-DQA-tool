import { AlertTriangle, CheckCircle2, CloudOff, Info } from "lucide-react";
import { cn } from "../../lib/cn";

type BannerVariant = "offline" | "pending" | "syncing" | "synced" | "failed" | "relogin" | "info";

const bannerStyles: Record<BannerVariant, string> = {
  offline: "border-amber-200 bg-amber-50 text-amber-900",
  pending: "border-cyan-200 bg-cyan-50 text-sky-900",
  syncing: "border-sky-200 bg-sky-50 text-sky-900",
  synced: "border-emerald-200 bg-emerald-50 text-emerald-900",
  failed: "border-rose-200 bg-rose-50 text-rose-900",
  relogin: "border-violet-200 bg-violet-50 text-violet-900",
  info: "border-slate-200 bg-white text-brand-text",
};

const bannerIcons = {
  offline: CloudOff,
  pending: Info,
  syncing: Info,
  synced: CheckCircle2,
  failed: AlertTriangle,
  relogin: AlertTriangle,
  info: Info,
};

export function SyncBanner({
  variant,
  message,
  className,
}: {
  variant: BannerVariant;
  message: string;
  className?: string;
}) {
  const Icon = bannerIcons[variant];
  return (
    <div className={cn("flex items-start gap-3 rounded-xl border px-4 py-3 text-sm", bannerStyles[variant], className)}>
      <Icon size={18} className="mt-0.5 shrink-0" />
      <p>{message}</p>
    </div>
  );
}
