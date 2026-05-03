import { AlertTriangle, CalendarClock, MapPinned, Rows3, ShieldCheck, Users } from "lucide-react";
import { Badge } from "../ui/Badge";
import type { AssessmentWorkspace } from "../../types";

export function AssessmentSummaryCard({
  workspace,
  missingRequiredCount,
}: {
  workspace: AssessmentWorkspace;
  missingRequiredCount: number;
}) {
  const sharedGroupLogin =
    workspace.assessment_facility.team_members.find((member) => member.team_role === "TEAM_LEAD" && member.is_active)
      ?.user?.full_name ?? workspace.assessment_facility.assigned_assessor?.full_name ?? "Not assigned";
  const sharedGroupEmail =
    workspace.assessment_facility.team_members.find((member) => member.team_role === "TEAM_LEAD" && member.is_active)
      ?.user?.email ?? workspace.assessment_facility.assigned_assessor?.email ?? "No shared email assigned";
  const dhis2Statuses = workspace.values.map((value) => value.dhis2_api_status ?? "NOT_PULLED");
  const hasDhis2Error = dhis2Statuses.some((status) => status === "ERROR" || status === "NOT_CONFIGURED");
  const hasDhis2Success = dhis2Statuses.some((status) => status === "SUCCESS");
  const completedRows = workspace.values.filter(
    (value) => value.register_value !== null && value.hmis105_value !== null,
  ).length;
  const totalRows = workspace.selected_indicators.length;
  const completionPercent = totalRows > 0 ? Math.round((completedRows / totalRows) * 100) : 0;
  const circumference = 150.8;
  const strokeOffset = circumference - (completionPercent / 100) * circumference;

  return (
    <section className="overflow-hidden rounded-[28px] border border-brand-border bg-white shadow-panel">
      <div className="relative overflow-hidden bg-[radial-gradient(circle_at_top_right,rgba(26,173,136,.35),transparent_34%),linear-gradient(135deg,#152638,#0f1e2e_58%,#0a7a5e)] px-6 py-4 text-white">
        <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <p className="text-[10px] uppercase tracking-[0.32em] text-emerald-100">Data quality assessment</p>
            <h1 className="mt-1 font-display text-2xl font-semibold leading-tight sm:text-3xl">
              {workspace.facility.facility_name}
            </h1>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge tone="success" className="border-white/15 bg-white/10 text-white">{workspace.assessment_round.assessment_code}</Badge>
              <Badge tone="neutral" className="border-white/15 bg-white/10 text-white">{workspace.assessment_round.reporting_period}</Badge>
              <Badge tone={workspace.workspace_mode === "EDIT" ? "success" : "warning"}>
                {workspace.workspace_mode === "EDIT" ? "Edit mode" : "Read-only mode"}
              </Badge>
            </div>
          </div>
          <div className="relative flex h-24 w-24 items-center justify-center">
            <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 56 56">
              <circle cx="28" cy="28" r="24" fill="none" stroke="rgba(255,255,255,.16)" strokeWidth="5" />
              <circle
                cx="28"
                cy="28"
                r="24"
                fill="none"
                stroke="#4ade80"
                strokeLinecap="round"
                strokeWidth="5"
                strokeDasharray={circumference}
                strokeDashoffset={strokeOffset}
                className="transition-all duration-700"
              />
            </svg>
            <div className="text-center">
              <p className="font-mono-ui text-xl font-semibold">{completionPercent}%</p>
              <p className="text-[10px] text-white/65">{completedRows}/{totalRows}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-[18px] bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <MapPinned size={16} />
            District
          </div>
          <p className="mt-2 font-semibold text-brand-text">{workspace.facility.district}</p>
        </div>

        <div className="rounded-[18px] bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <Users size={16} />
            Shared group account
          </div>
          <p className="mt-2 font-semibold text-brand-text">{sharedGroupLogin}</p>
          <p className="mt-1 text-sm text-brand-muted">{sharedGroupEmail}</p>
        </div>

        <div className="rounded-[18px] bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <CalendarClock size={16} />
            Deadline
          </div>
          <p className="mt-2 font-semibold text-brand-text">{workspace.assessment_round.deadline ?? "Not set"}</p>
        </div>

        <div className="rounded-[18px] bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <Rows3 size={16} />
            Indicators
          </div>
          <p className="mt-2 font-semibold text-brand-text">{workspace.selected_indicators.length}</p>
        </div>

        <div className="rounded-[18px] bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <AlertTriangle size={16} />
            Required missing
          </div>
          <p className="mt-2 font-semibold text-brand-text">{missingRequiredCount}</p>
        </div>

        <div className="rounded-[18px] bg-brand-surface px-4 py-4">
          <div className="flex items-center gap-2 text-brand-muted">
            <ShieldCheck size={16} />
            DHIS2 pull
          </div>
          <p className="mt-2 font-semibold text-brand-text">
            {hasDhis2Error ? "Needs attention" : hasDhis2Success ? "Values loaded" : "Not pulled"}
          </p>
        </div>
      </div>
    </section>
  );
}
