import { FileText } from "lucide-react";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import type { ReportType } from "../../types";

export function ReportTypeCard({
  title,
  description,
  reportType,
  selected,
  onSelect,
}: {
  title: string;
  description: string;
  reportType: ReportType;
  selected: boolean;
  onSelect: (reportType: ReportType) => void;
}) {
  return (
    <Card className={selected ? "ring-2 ring-brand-teal/50" : ""}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-brand-surface p-3 text-brand-teal">
              <FileText size={18} />
            </div>
            <h3 className="text-lg font-semibold text-brand-text">{title}</h3>
          </div>
          <p className="mt-3 text-sm text-brand-muted">{description}</p>
        </div>
        <Button variant={selected ? "primary" : "secondary"} onClick={() => onSelect(reportType)}>
          {selected ? "Selected" : "Choose"}
        </Button>
      </div>
    </Card>
  );
}
