import { useState } from "react";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Textarea } from "../ui/Textarea";
import type { CorrectiveActionPayload, DqaIssueType, SeverityLevel } from "../../types";

const ISSUE_TYPES: DqaIssueType[] = [
  "REGISTER_TO_HMIS_SUMMARIZATION_ERROR",
  "DHIS2_DATA_ENTRY_ERROR",
  "MULTIPLE_STAGE_ERROR",
  "SOURCE_DOCUMENT_ISSUE",
  "HMIS105_REPORT_MISSING",
  "DHIS2_VALUE_MISSING",
  "VALUE_MISSING",
  "REQUIRES_REVIEW",
];

const SEVERITIES: SeverityLevel[] = ["MINOR", "MODERATE", "MAJOR", "CRITICAL", "MISSING"];

export function CorrectiveActionForm({
  initialValue,
  onSubmit,
  submitLabel = "Create action",
}: {
  initialValue?: Partial<CorrectiveActionPayload>;
  onSubmit: (payload: CorrectiveActionPayload) => Promise<void>;
  submitLabel?: string;
}) {
  const [payload, setPayload] = useState<CorrectiveActionPayload>({
    issue_type: initialValue?.issue_type ?? "REQUIRES_REVIEW",
    severity: initialValue?.severity ?? "MAJOR",
    action_description: initialValue?.action_description ?? "",
    recommended_action: initialValue?.recommended_action ?? null,
    responsible_person: initialValue?.responsible_person ?? null,
    deadline: initialValue?.deadline ?? null,
    manager_comment: initialValue?.manager_comment ?? null,
    assessor_comment: initialValue?.assessor_comment ?? null,
    assessment_facility_id: initialValue?.assessment_facility_id ?? null,
    dqa_value_id: initialValue?.dqa_value_id ?? null,
    indicator_id: initialValue?.indicator_id ?? null,
    facility_id: initialValue?.facility_id ?? null,
    assessment_round_id: initialValue?.assessment_round_id ?? null,
    assigned_to_user_id: initialValue?.assigned_to_user_id ?? null,
  });
  const [saving, setSaving] = useState(false);

  return (
    <Card title="Corrective Action" subtitle="Track who will follow up on the discrepancy and how it will be verified.">
      <div className="grid gap-4 md:grid-cols-2">
        <Select value={payload.issue_type} onChange={(event) => setPayload((current) => ({ ...current, issue_type: event.target.value as DqaIssueType }))}>
          {ISSUE_TYPES.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </Select>
        <Select value={payload.severity} onChange={(event) => setPayload((current) => ({ ...current, severity: event.target.value as SeverityLevel }))}>
          {SEVERITIES.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </Select>
        <Input placeholder="Responsible person" value={payload.responsible_person ?? ""} onChange={(event) => setPayload((current) => ({ ...current, responsible_person: event.target.value || null }))} />
        <Input type="date" value={payload.deadline ?? ""} onChange={(event) => setPayload((current) => ({ ...current, deadline: event.target.value || null }))} />
      </div>
      <div className="mt-4 space-y-4">
        <Textarea rows={3} placeholder="Action description" value={payload.action_description} onChange={(event) => setPayload((current) => ({ ...current, action_description: event.target.value }))} />
        <Textarea rows={3} placeholder="Recommended action" value={payload.recommended_action ?? ""} onChange={(event) => setPayload((current) => ({ ...current, recommended_action: event.target.value || null }))} />
      </div>
      <div className="mt-4">
        <Button
          onClick={async () => {
            setSaving(true);
            try {
              await onSubmit(payload);
            } finally {
              setSaving(false);
            }
          }}
          disabled={saving || !payload.action_description.trim()}
        >
          {saving ? "Saving..." : submitLabel}
        </Button>
      </div>
    </Card>
  );
}
