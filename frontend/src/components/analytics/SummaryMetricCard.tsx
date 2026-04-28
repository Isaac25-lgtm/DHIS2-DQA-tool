import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";

export function SummaryMetricCard({
  title,
  value,
  helper,
  tone = "info",
}: {
  title: string;
  value: string | number;
  helper?: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}) {
  return (
    <Card>
      <div className="space-y-3">
        <Badge tone={tone}>{title}</Badge>
        <p className="text-4xl font-extrabold tracking-tight text-brand-navy">{value}</p>
        {helper ? <p className="text-sm text-brand-muted">{helper}</p> : null}
      </div>
    </Card>
  );
}
