import { AlertTriangle, ShieldAlert } from "lucide-react";
import { Card } from "../ui/Card";

type Finding = {
  finding_number?: number;
  finding_title?: string;
  evidence?: string;
  implication?: string;
  required_action?: string;
};

type ChaseRow = {
  facility?: string;
  administrative_area?: string;
  indicator?: string;
  hmis_code?: string;
  gap?: number | null;
  pattern?: string;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

export function ReportFindingPreview({ structured }: { structured: Record<string, unknown> }) {
  const blocks = asRecord(structured.finding_blocks);
  const findings = asArray<Finding>(blocks.findings);
  const chaseList = asArray<ChaseRow>(structured.critical_chase_list);
  const sync = asRecord(structured.dhis2_sync_summary);
  const responseClassification = asRecord(sync.response_classification);
  const noDataCount = Number(responseClassification.NO_DATA ?? sync.dhis2_no_data_count ?? 0);
  const sourceNotAssessed = structured.source_document_assessment_status === "NOT_ASSESSED";

  if (!findings.length && !chaseList.length && !noDataCount && !sourceNotAssessed) {
    return null;
  }

  return (
    <Card title="Finding-block preview" subtitle="Management-facing structure that will drive the export package.">
      <div className="space-y-4">
        {sourceNotAssessed ? (
          <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <p>Source document quality was not fully measured in this round.</p>
          </div>
        ) : null}
        {noDataCount > 0 ? (
          <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <p>{noDataCount} DHIS2 no-data row{noDataCount === 1 ? "" : "s"} require separate verification before being treated as zero.</p>
          </div>
        ) : null}
        {chaseList.length ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-red-900">
              <ShieldAlert size={16} />
              Critical chase list
            </div>
            <div className="space-y-2">
              {chaseList.slice(0, 5).map((row, index) => (
                <p key={`${row.facility}-${row.hmis_code}-${index}`} className="text-xs text-red-900">
                  {row.facility ?? "Facility"} - {row.indicator ?? "Indicator"} ({row.hmis_code ?? "HMIS"}), gap {row.gap ?? "N/A"}, {row.pattern ?? "requires review"}.
                </p>
              ))}
            </div>
          </div>
        ) : null}
        {findings.length ? (
          <div className="space-y-3">
            {findings.slice(0, 7).map((finding, index) => (
              <div key={`${finding.finding_number}-${index}`} className="rounded-2xl border border-brand-border bg-white px-4 py-3">
                <p className="text-sm font-semibold text-brand-text">
                  Finding {finding.finding_number ?? index + 1}: {finding.finding_title ?? "Untitled finding"}
                </p>
                <p className="mt-1 text-xs leading-5 text-brand-muted">{finding.evidence}</p>
                <p className="mt-2 text-xs leading-5 text-brand-text">Action: {finding.required_action ?? "Review required."}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </Card>
  );
}
