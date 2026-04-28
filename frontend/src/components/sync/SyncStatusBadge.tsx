import { AlertTriangle, CheckCircle2, Clock3, CloudOff, CloudUpload, Save } from "lucide-react";
import { Badge } from "../ui/Badge";

type SyncTone = "neutral" | "success" | "warning" | "danger" | "info";

const toneMap: Record<string, SyncTone> = {
  CACHED: "info",
  LOCAL_DRAFT: "info",
  DRAFT_SAVED_LOCALLY: "info",
  PENDING_SYNC: "warning",
  SYNCING: "info",
  SYNCED: "success",
  SYNC_FAILED: "danger",
  RELOGIN_REQUIRED: "warning",
  SERVER_SAVED: "success",
  ONLINE: "success",
  OFFLINE: "warning",
};

const iconMap = {
  CACHED: Save,
  LOCAL_DRAFT: Save,
  DRAFT_SAVED_LOCALLY: Save,
  PENDING_SYNC: Clock3,
  SYNCING: CloudUpload,
  SYNCED: CheckCircle2,
  SYNC_FAILED: CloudOff,
  RELOGIN_REQUIRED: AlertTriangle,
  SERVER_SAVED: CheckCircle2,
  ONLINE: CheckCircle2,
  OFFLINE: CloudOff,
  DEFAULT: AlertTriangle,
};

export function SyncStatusBadge({ status }: { status: string }) {
  const Icon = iconMap[status as keyof typeof iconMap] ?? iconMap.DEFAULT;
  return (
    <Badge tone={toneMap[status] ?? "neutral"} className="gap-1">
      <Icon size={14} />
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
