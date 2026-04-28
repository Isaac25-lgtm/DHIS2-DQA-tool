import { AlertTriangle, DatabaseZap, RefreshCcw } from "lucide-react";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import type { Dhis2Value } from "../../types";

export function Dhis2ValuePanel({
  values,
  message,
  onRetry,
  retrying,
  disabled,
}: {
  values: Dhis2Value[];
  message: string | null;
  onRetry: () => void;
  retrying: boolean;
  disabled: boolean;
}) {
  const successCount = values.filter((item) => item.status === "SUCCESS").length;
  const noDataCount = values.filter((item) => item.status === "NO_DATA").length;
  const errorCount = values.filter((item) => item.status === "ERROR").length;

  return (
    <Card title="DHIS2 values" subtitle="System values are pulled server-side using the facility org unit and reporting period.">
      <div className="flex flex-wrap items-center gap-3">
        <Badge tone="success">{successCount} success</Badge>
        <Badge tone="warning">{noDataCount} no data</Badge>
        <Badge tone="danger">{errorCount} errors</Badge>
        <Button variant="secondary" className="gap-2" onClick={onRetry} disabled={disabled || retrying}>
          <RefreshCcw size={16} />
          {retrying ? "Syncing..." : "Sync with DHIS2"}
        </Button>
      </div>

      {message ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <p>{message}</p>
          </div>
        </div>
      ) : null}

      <div className="mt-4 space-y-3">
        {values.slice(0, 5).map((item) => (
          <div key={item.indicator_id} className="flex items-center justify-between rounded-xl bg-brand-surface px-4 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-brand-text">{item.dhis2_uid_or_operand ?? "UID pending"}</p>
              <p className="mt-1 text-xs text-brand-muted">
                {item.extracted_at ? `Pulled ${new Date(item.extracted_at).toLocaleString()}` : "Not pulled yet"}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge tone={item.status === "SUCCESS" ? "success" : item.status === "ERROR" ? "danger" : "warning"}>
                {item.status ?? "PENDING"}
              </Badge>
              <div className="flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-brand-navy">
                <DatabaseZap size={16} />
                {item.value ?? "-"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
