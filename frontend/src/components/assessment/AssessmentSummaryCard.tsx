import { AlertTriangle, CalendarClock, MapPinned, Rows3, ShieldCheck, Users } from "lucide-react";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import type { AssessmentWorkspace } from "../../types";

export function AssessmentSummaryCard({
  workspace,
  missingRequiredCount,
}: {
  workspace: AssessmentWorkspace;
  missingRequiredCount: number;
}) {
  const teamLead =
    workspace.assessment_facility.team_members.find((member) => member.team_role === "TEAM_LEAD" && member.is_active)
      ?.user?.full_name ?? workspace.assessment_facility.assigned_assessor?.full_name ?? "Not assigned";
  const teamMembers = workspace.assessment_facility.team_members
    .filter((member) => member.team_role === "TEAM_MEMBER" && member.is_active)
    .map((member) => member.user?.full_name ?? "Unnamed team member");
  const dhis2Statuses = workspace.values.map((value) => value.dhis2_api_status ?? "NOT_PULLED");
  const hasDhis2Error = dhis2Statuses.some((status) => status === "ERROR" || status === "NOT_CONFIGURED");
  const hasDhis2Success = dhis2Statuses.some((status) => status === "SUCCESS");

  return (
    <Card
      title={workspace.assessment_round.name}
      subtitle="Online assessor workspace with server-side DHIS2 auto-population."
      className="border-brand-border/70"
    >
      <div className="flex flex-wrap gap-2">
        <Badge tone="info">{workspace.facility.facility_name}</Badge>
        <Badge tone="neutral">{workspace.assessment_round.reporting_period}</Badge>
        <Badge tone={workspace.workspace_mode === "EDIT" ? "success" : "warning"}>
          {workspace.workspace_mode === "EDIT" ? "Edit mode" : "Read-only mode"}
        </Badge>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <MapPinned size={16} />
            Facility
          </div>
          <p className="mt-2 font-semibold text-brand-text">{workspace.facility.facility_name}</p>
          <p className="mt-1 text-sm text-brand-muted">{workspace.facility.district}</p>
        </div>

        <div className="rounded-xl bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <Users size={16} />
            Field team
          </div>
          <p className="mt-2 font-semibold text-brand-text">{teamLead}</p>
          <p className="mt-1 text-sm text-brand-muted">
            {teamMembers.length > 0 ? teamMembers.join(", ") : "No team members listed"}
          </p>
        </div>

        <div className="rounded-xl bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <CalendarClock size={16} />
            Deadline
          </div>
          <p className="mt-2 font-semibold text-brand-text">{workspace.assessment_round.deadline ?? "Not set"}</p>
        </div>

        <div className="rounded-xl bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <Rows3 size={16} />
            Indicators
          </div>
          <p className="mt-2 font-semibold text-brand-text">{workspace.selected_indicators.length}</p>
        </div>

        <div className="rounded-xl bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <AlertTriangle size={16} />
            Required missing
          </div>
          <p className="mt-2 font-semibold text-brand-text">{missingRequiredCount}</p>
        </div>

        <div className="rounded-xl bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <ShieldCheck size={16} />
            DHIS2 pull
          </div>
          <p className="mt-2 font-semibold text-brand-text">
            {hasDhis2Error ? "Needs attention" : hasDhis2Success ? "Values loaded" : "Not pulled"}
          </p>
          <p className="mt-1 text-sm text-brand-muted">Status is based on field-time DHIS2 extraction metadata.</p>
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-dashed border-brand-border bg-brand-surface px-4 py-3 text-sm text-brand-muted">
        <div className="flex items-center gap-2 text-brand-text">
          <ShieldCheck size={16} className="text-brand-teal" />
          This assessment will support offline draft entry in the next release.
        </div>
      </div>
    </Card>
  );
}
