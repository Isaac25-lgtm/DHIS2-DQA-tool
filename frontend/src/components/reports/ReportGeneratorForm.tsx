import { useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import type { AssessmentFacilityAssignment, AssessmentRoundListItem, ReportGeneratePayload, ReportType } from "../../types";

const REPORT_OPTIONS: Array<{ label: string; value: ReportType }> = [
  { label: "Facility DQA Report", value: "FACILITY_DQA_REPORT" },
  { label: "Consolidated UCMB DQA Report", value: "CONSOLIDATED_UCMB_DQA_REPORT" },
  { label: "Corrective Action Report", value: "CORRECTIVE_ACTION_REPORT" },
  { label: "Executive Summary", value: "EXECUTIVE_SUMMARY" },
];

export function ReportGeneratorForm({
  value,
  rounds,
  facilities,
  onChange,
  onSubmit,
  loading,
}: {
  value: ReportGeneratePayload;
  rounds: AssessmentRoundListItem[];
  facilities: AssessmentFacilityAssignment[];
  onChange: (updates: Partial<ReportGeneratePayload>) => void;
  onSubmit: () => void;
  loading: boolean;
}) {
  const facilityRequired = value.report_type === "FACILITY_DQA_REPORT";
  const roundOptions = useMemo(
    () =>
      rounds.map((round) => ({
        label: `${round.assessment_code} - ${round.name} (${round.reporting_period})`,
        value: round.id,
      })),
    [rounds],
  );
  const facilityOptions = useMemo(
    () => facilities.map((item) => ({ label: item.facility.facility_name, value: item.id })),
    [facilities],
  );

  return (
    <div className="space-y-4">
      <label className="block space-y-2">
        <span className="text-sm font-semibold text-brand-text">Report type</span>
        <Select
          value={value.report_type}
          onChange={(event) => onChange({ report_type: event.target.value as ReportType, assessment_facility_id: null })}
        >
          {REPORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </label>
      <label className="block space-y-2">
        <span className="text-sm font-semibold text-brand-text">Assessment round</span>
        <Select
          value={value.assessment_round_id ?? ""}
          onChange={(event) => onChange({ assessment_round_id: event.target.value || null })}
        >
          <option value="">Select an assessment round</option>
          {roundOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </label>
      {facilityRequired ? (
        <label className="block space-y-2">
          <span className="text-sm font-semibold text-brand-text">Assessment facility</span>
          <Select
            value={value.assessment_facility_id ?? ""}
            onChange={(event) => onChange({ assessment_facility_id: event.target.value || null })}
          >
            <option value="">Select an assessment facility</option>
            {facilityOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </label>
      ) : null}
      <label className="flex items-start gap-3 rounded-2xl border border-brand-border bg-brand-surface px-4 py-3">
        <input
          type="checkbox"
          className="mt-1"
          checked={value.include_comments}
          onChange={(event) => onChange({ include_comments: event.target.checked })}
        />
        <div>
          <p className="text-sm font-semibold text-brand-text">Include assessor and manager comments</p>
          <p className="mt-1 text-xs text-brand-muted">
            Comments may contain informal field notes and are excluded from management reports by default. Include them only when you intentionally want the AI or template report to summarize them for audit review.
          </p>
        </div>
      </label>
      {value.include_comments ? (
        <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <p>The structured payload will include comments and this will be logged for review.</p>
        </div>
      ) : null}
      <Button onClick={onSubmit} disabled={loading}>
        {loading ? "Generating..." : "Generate report"}
      </Button>
    </div>
  );
}
