import { Badge } from "../ui/Badge";
import type { ReportStatus } from "../../types";

const toneMap: Record<ReportStatus, "neutral" | "success" | "warning" | "danger" | "info"> = {
  DRAFT: "warning",
  GENERATED: "info",
  REVIEWED: "info",
  APPROVED: "success",
  EXPORTED: "success",
  ARCHIVED: "neutral",
};

export function ReportStatusBadge({ status }: { status: ReportStatus }) {
  return <Badge tone={toneMap[status] ?? "neutral"}>{status.replace(/_/g, " ")}</Badge>;
}
