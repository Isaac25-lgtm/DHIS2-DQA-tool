import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  ActivitySquare,
  ArrowUpRight,
  Building2,
  ClipboardCheck,
  ClipboardList,
  FileText,
  Layers3,
  RefreshCcw,
  ShieldAlert,
  Users,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Table } from "../components/ui/Table";
import { useAuth } from "../hooks/useAuth";
import { analyticsService } from "../services/analyticsService";
import { assessmentAssignmentService } from "../services/assessmentAssignmentService";
import { assessmentRoundService } from "../services/assessmentRoundService";
import { correctiveActionService } from "../services/correctiveActionService";
import { facilityService } from "../services/facilityService";
import {
  getPendingSyncCount,
  listCachedAssessments,
} from "../services/offlineStore";
import { reportService } from "../services/reportService";
import { userService } from "../services/userService";
import { indicatorService } from "../services/indicatorService";
import type {
  AnalyticsSummary,
  AssessmentRoundListItem,
  CorrectiveAction,
  DashboardStat,
  MyAssessmentListItem,
  Report,
} from "../types";

const trendData = [
  { label: "Week 1", exactRate: 64, critical: 9 },
  { label: "Week 2", exactRate: 68, critical: 7 },
  { label: "Week 3", exactRate: 74, critical: 5 },
  { label: "Week 4", exactRate: 79, critical: 3 },
];

const reportColumns: ColumnDef<Report>[] = [
  { accessorKey: "title", header: "Report" },
  {
    accessorKey: "report_type",
    header: "Type",
    cell: ({ row }) => (
      <span className="text-sm text-brand-muted">
        {row.original.report_type.replace(/_/g, " ")}
      </span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const value = row.original.status;
      const tone =
        value === "APPROVED" || value === "EXPORTED"
          ? "success"
          : value === "REVIEWED"
            ? "info"
            : "warning";
      return <Badge tone={tone}>{value.replace(/_/g, " ")}</Badge>;
    },
  },
  {
    accessorKey: "generated_at",
    header: "Generated",
    cell: ({ row }) => (
      <span className="text-sm text-brand-muted">
        {row.original.generated_at ? new Date(row.original.generated_at).toLocaleString() : "Pending"}
      </span>
    ),
  },
];

const assessmentColumns: ColumnDef<MyAssessmentListItem>[] = [
  { accessorKey: "facility_name", header: "Facility" },
  { accessorKey: "round_name", header: "Assessment round" },
  { accessorKey: "reporting_period", header: "Period" },
  {
    accessorKey: "deadline",
    header: "Deadline",
    cell: ({ row }) => row.original.deadline ?? "Not set",
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const value = row.original.status;
      const tone =
        value === "SUBMITTED"
          ? "success"
          : value === "IN_PROGRESS" || value === "DRAFT_SAVED"
            ? "warning"
            : "info";
      return <Badge tone={tone}>{value.replace(/_/g, " ")}</Badge>;
    },
  },
];

function nextDeadline(items: MyAssessmentListItem[]) {
  return items
    .filter((item) => item.deadline)
    .sort((left, right) => (left.deadline ?? "").localeCompare(right.deadline ?? ""))[0]?.deadline ?? null;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStat[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [myAssessments, setMyAssessments] = useState<MyAssessmentListItem[]>([]);
  const [actions, setActions] = useState<CorrectiveAction[]>([]);
  const [assessmentRounds, setAssessmentRounds] = useState<AssessmentRoundListItem[]>([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string>("");
  const [pendingSyncCount, setPendingSyncCount] = useState(0);
  const [cachedCount, setCachedCount] = useState(0);

  useEffect(() => {
    const loadDashboard = async () => {
      setLoading(true);
      try {
        const role = user?.role;

        const [
          analyticsSummary,
          fetchedReports,
          fetchedActions,
          fetchedAssessments,
          pendingSync,
          cachedAssessments,
          userCount,
          facilityCount,
          indicatorCount,
          fetchedRounds,
        ] = await Promise.all([
          role === "MANAGER" || role === "REVIEWER" || role === "VIEWER"
            ? analyticsService.getOverallSummary().catch(() => null)
            : Promise.resolve(null),
          role === "MANAGER" || role === "REVIEWER" || role === "VIEWER"
            ? reportService.listReports().catch(() => [])
            : Promise.resolve([]),
          role === "MANAGER" || role === "REVIEWER" || role === "ASSESSOR"
            ? correctiveActionService.listActions().catch(() => [])
            : Promise.resolve([]),
          role === "ASSESSOR"
            ? assessmentAssignmentService.listMyAssessments().catch(() => [])
            : Promise.resolve([]),
          getPendingSyncCount().catch(() => 0),
          listCachedAssessments().catch(() => []),
          role === "MANAGER" ? userService.listUsers().then((items) => items.length).catch(() => null) : Promise.resolve(null),
          role === "MANAGER" ? facilityService.listFacilities().then((items) => items.length).catch(() => null) : Promise.resolve(null),
          role === "MANAGER" ? indicatorService.listIndicators({ active: true }).then((items) => items.length).catch(() => null) : Promise.resolve(null),
          role === "MANAGER" || role === "REVIEWER"
            ? assessmentRoundService.listRounds().catch(() => [])
            : Promise.resolve([]),
        ]);

        setAnalytics(analyticsSummary);
        setReports(fetchedReports.slice(0, 5));
        setActions(fetchedActions);
        setAssessmentRounds(fetchedRounds);
        setSelectedAssessmentId((current) => current || fetchedRounds[0]?.id || "");
        setMyAssessments(fetchedAssessments);
        setPendingSyncCount(pendingSync);
        setCachedCount(cachedAssessments.length);

        if (role === "MANAGER") {
          setStats([
            {
              label: "Active assessment rounds",
              value: String(fetchedRounds.length),
              trend: "Manager workflow live",
              description: "Draft, published, and closed rounds are now managed end to end.",
            },
            {
              label: "Facilities assessed",
              value: String(analyticsSummary?.facilities_assessed ?? 0),
              trend: `${analyticsSummary?.facilities_pending ?? 0} pending`,
              description: "Published assessment progress is now visible from the dashboard.",
            },
            {
              label: "Exact match rate",
              value: analyticsSummary ? `${analyticsSummary.exact_match_rate.toFixed(1)}%` : "--",
              trend: `${analyticsSummary?.major_discrepancy_rate.toFixed(1) ?? 0}% major`,
              description: "Calculated from comparison results using field-time DHIS2 values.",
            },
            {
              label: "Open corrective actions",
              value: String(
                fetchedActions.filter((item) => ["OPEN", "IN_PROGRESS", "OVERDUE"].includes(item.status)).length,
              ),
              trend: `${fetchedActions.filter((item) => item.status === "OVERDUE").length} overdue`,
              description: "Corrective actions now support review, verification, and closure states.",
            },
            {
              label: "Users",
              value: String(userCount ?? 0),
              trend: "Role-based access",
              description: "Managers continue to control system users, permissions, and accountability.",
            },
            {
              label: "Facilities in registry",
              value: String(facilityCount ?? 0),
              trend: "DHIS2-linked",
              description: "Registry facilities carry DHIS2 org unit UIDs for workspace pulls and reporting scope.",
            },
            {
              label: "Active indicators",
              value: String(indicatorCount ?? 0),
              trend: "Manager-selected",
              description: "Indicator selection remains manager controlled at the round level.",
            },
            {
              label: "Recent reports",
              value: String(fetchedReports.length),
              trend: `${fetchedReports.filter((item) => item.status === "APPROVED" || item.status === "EXPORTED").length} approved/exported`,
              description: "Report drafting, review, approval, and export workflow is live.",
            },
          ]);
          return;
        }

        if (role === "ASSESSOR") {
          const submittedCount = fetchedAssessments.filter((item) => item.status === "SUBMITTED").length;
          const draftCount = fetchedAssessments.filter((item) =>
            ["IN_PROGRESS", "DRAFT_SAVED", "PENDING_SYNC", "ASSIGNED", "NOT_STARTED"].includes(item.status),
          ).length;
          setStats([
            {
              label: "Assigned assessments",
              value: String(fetchedAssessments.length),
              trend: `${draftCount} active`,
              description: "Only your assigned facility workspaces are visible and editable.",
            },
            {
              label: "Pending sync",
              value: String(pendingSync),
              trend: pendingSync > 0 ? "Needs connection" : "Sync clear",
              description: "Offline drafts remain on the device until you sync them successfully.",
            },
            {
              label: "Submitted assessments",
              value: String(submittedCount),
              trend: nextDeadline(fetchedAssessments) ? `Next deadline ${nextDeadline(fetchedAssessments)}` : "No deadline set",
              description: "Submitted assessments become read-only unless returned for correction later.",
            },
            {
              label: "Cached offline packages",
              value: String(cachedAssessments.length),
              trend: "Offline ready",
              description: "Previously opened assignments remain available for offline entry on this device.",
            },
          ]);
          return;
        }

        if (role === "REVIEWER") {
          setStats([
            {
              label: "Assessment rounds",
              value: String(fetchedRounds.length),
              trend: "Review scope live",
              description: "Reviewers can inspect round performance, results, and corrective action follow-up.",
            },
            {
              label: "Critical discrepancies",
              value: String(analyticsSummary?.critical_discrepancy_count ?? 0),
              trend: `${analyticsSummary?.major_discrepancy_rate.toFixed(1) ?? 0}% major rate`,
              description: "Critical counts highlight facilities or indicators that need urgent follow-up.",
            },
            {
              label: "Need verification",
              value: String(
                fetchedActions.filter((item) => item.status === "RESOLVED" || item.status === "IN_PROGRESS").length,
              ),
              trend: `${fetchedActions.filter((item) => item.status === "VERIFIED").length} verified`,
              description: "Resolved actions still need evidence-based verification before final closure.",
            },
            {
              label: "Reports available",
              value: String(fetchedReports.length),
              trend: `${fetchedReports.filter((item) => item.status === "REVIEWED").length} reviewed`,
              description: "Draft and reviewed reports remain available for structured feedback and approval flow.",
            },
          ]);
          return;
        }

        setStats([
          {
            label: "Approved reports",
            value: String(fetchedReports.filter((item) => item.status === "APPROVED" || item.status === "EXPORTED").length),
            trend: "Viewer access",
            description: "Viewer access remains read-only and report-led.",
          },
          {
            label: "Exact match rate",
            value: analyticsSummary ? `${analyticsSummary.exact_match_rate.toFixed(1)}%` : "--",
            trend: `${analyticsSummary?.critical_discrepancy_count ?? 0} critical`,
            description: "Viewer analytics remain focused on approved, high-level data quality status.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    void loadDashboard();
  }, [user?.role]);

  const roleSummary = useMemo(() => {
    switch (user?.role) {
      case "MANAGER":
        return "Comparison analytics, corrective action tracking, and report generation are now available from one operational dashboard.";
      case "ASSESSOR":
        return "Your dashboard now combines assignment progress, offline readiness, and sync awareness for field work.";
      case "REVIEWER":
        return "You can now focus on submitted assessments, critical discrepancies, and action verification work.";
      case "VIEWER":
        return "This view stays read-only and highlights approved analytics and reports.";
      default:
        return "Authenticated platform overview.";
    }
  }, [user?.role]);

  const selectedAssessment = useMemo(
    () => assessmentRounds.find((item) => item.id === selectedAssessmentId) ?? assessmentRounds[0] ?? null,
    [assessmentRounds, selectedAssessmentId],
  );

  const selectedProgress = selectedAssessment?.completion_percent ?? 0;
  const selectedRemaining = Math.max(0, 100 - selectedProgress);

  return (
    <div className="space-y-6">
      <Card title="Platform Status" subtitle={roleSummary}>
        <div className="flex flex-wrap gap-3">
          <Badge tone="success">Reporting enabled</Badge>
          <Badge tone="info">PostgreSQL-only platform</Badge>
          <Badge tone="info">Offline drafts enabled</Badge>
          {analytics ? (
            <Badge tone="warning">
              {analytics.critical_discrepancy_count} critical discrepancies
            </Badge>
          ) : null}
        </div>
      </Card>

      {user?.role === "MANAGER" ? (
        <Card title="Select Assessment to Monitor" subtitle="Choose one assessment round to focus dashboard progress and follow-up.">
          <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
            <label className="block">
              <span className="text-sm font-semibold text-brand-text">Assessment</span>
              <select
                className="mt-2 w-full rounded-2xl border border-brand-border px-4 py-3 text-sm outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20"
                value={selectedAssessment?.id ?? ""}
                onChange={(event) => setSelectedAssessmentId(event.target.value)}
              >
                {assessmentRounds.length === 0 ? <option value="">No assessments yet</option> : null}
                {assessmentRounds.map((round) => (
                  <option key={round.id} value={round.id}>
                    {round.name} - {round.reporting_period} - {round.status.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </label>
            <div className="rounded-2xl bg-brand-surface px-5 py-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-brand-text">{selectedAssessment?.name ?? "No assessment selected"}</p>
                  <p className="mt-1 text-sm text-brand-muted">
                    {selectedAssessment
                      ? `${selectedAssessment.reporting_period} - ${selectedAssessment.facility_count} facilities - ${selectedAssessment.indicator_count} indicators`
                      : "Create an assessment round to begin monitoring."}
                  </p>
                  {selectedAssessment?.start_date && selectedAssessment?.end_date ? (
                    <p className="mt-1 text-xs text-brand-muted">
                      Reporting window: {selectedAssessment.start_date} to {selectedAssessment.end_date}
                    </p>
                  ) : null}
                </div>
                {selectedAssessment ? <Badge tone="info">{selectedAssessment.status.replace(/_/g, " ")}</Badge> : null}
              </div>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-white">
                <div className="h-full rounded-full bg-brand-teal" style={{ width: `${selectedProgress}%` }} />
              </div>
              <p className="mt-2 text-xs text-brand-muted">
                {selectedProgress.toFixed(1)}% complete - {selectedRemaining.toFixed(1)}% remaining - {selectedAssessment?.assigned_facility_count ?? 0} teams assigned
              </p>
            </div>
          </div>
        </Card>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat, index) => {
          const icons = [
            ClipboardList,
            ActivitySquare,
            ShieldAlert,
            FileText,
            Users,
            Building2,
            Layers3,
            RefreshCcw,
          ];
          const Icon = icons[index % icons.length];
          return (
            <Card key={stat.label}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-brand-muted">{stat.label}</p>
                  <p className="mt-3 text-4xl font-extrabold tracking-tight text-brand-navy">{loading ? "--" : stat.value}</p>
                  <p className="mt-2 text-sm text-brand-muted">{stat.description}</p>
                </div>
                <div className="rounded-2xl bg-brand-surface p-3 text-brand-teal">
                  <Icon size={22} />
                </div>
              </div>
              <div className="mt-6 flex items-center gap-2 text-sm font-semibold text-brand-teal">
                <ArrowUpRight size={16} />
                {loading ? "Refreshing..." : stat.trend}
              </div>
            </Card>
          );
        })}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <Card
          title={user?.role === "ASSESSOR" ? "Field Work Snapshot" : "Quality Trend Snapshot"}
          subtitle={
            user?.role === "ASSESSOR"
              ? "Offline-safe entry, sync discipline, and assignment visibility now sit alongside the online workspace."
              : "Comparison logic and reporting share the same data quality model."
          }
        >
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="dqaExact" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00A6A6" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#00A6A6" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5EDF5" />
                <XAxis dataKey="label" stroke="#64748B" />
                <YAxis stroke="#64748B" />
                <Tooltip />
                <Area type="monotone" dataKey="exactRate" stroke="#00A6A6" fill="url(#dqaExact)" strokeWidth={3} />
                <Area type="monotone" dataKey="critical" stroke="#EF4444" fillOpacity={0} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Quick Actions" subtitle="The next best action depends on your role.">
          <div className="space-y-3">
            {user?.role === "MANAGER" ? (
              <>
                <Button className="w-full justify-between" onClick={() => navigate("/analytics")}>
                  Open analytics
                  <ArrowUpRight size={16} />
                </Button>
                <Button variant="secondary" className="w-full justify-between" onClick={() => navigate("/reports/generate")}>
                  Generate report
                  <ArrowUpRight size={16} />
                </Button>
                <Button variant="secondary" className="w-full justify-between" onClick={() => navigate("/corrective-actions")}>
                  Review corrective actions
                  <ArrowUpRight size={16} />
                </Button>
              </>
            ) : null}
            {user?.role === "ASSESSOR" ? (
              <>
                <Button className="w-full justify-between" onClick={() => navigate("/my-assessments")}>
                  Open my assessments
                  <ArrowUpRight size={16} />
                </Button>
                <div className="rounded-2xl border border-brand-border bg-white px-4 py-4 text-sm text-brand-muted">
                  {pendingSyncCount > 0
                    ? `${pendingSyncCount} draft${pendingSyncCount === 1 ? "" : "s"} waiting to sync.`
                    : "All local drafts are currently synced."}
                </div>
                <div className="rounded-2xl border border-brand-border bg-white px-4 py-4 text-sm text-brand-muted">
                  {cachedCount > 0
                    ? `${cachedCount} assessment package${cachedCount === 1 ? "" : "s"} cached for offline use on this device.`
                    : "Open an assigned assessment online once to make it available offline."}
                </div>
              </>
            ) : null}
            {user?.role === "REVIEWER" ? (
              <>
                <Button className="w-full justify-between" onClick={() => navigate("/analytics")}>
                  Review analytics
                  <ArrowUpRight size={16} />
                </Button>
                <Button variant="secondary" className="w-full justify-between" onClick={() => navigate("/corrective-actions")}>
                  Verify actions
                  <ArrowUpRight size={16} />
                </Button>
                <Button variant="secondary" className="w-full justify-between" onClick={() => navigate("/reports")}>
                  Inspect reports
                  <ArrowUpRight size={16} />
                </Button>
              </>
            ) : null}
            {user?.role === "VIEWER" ? (
              <>
                <Button className="w-full justify-between" onClick={() => navigate("/reports")}>
                  Browse approved reports
                  <ArrowUpRight size={16} />
                </Button>
                <Button variant="secondary" className="w-full justify-between" onClick={() => navigate("/analytics")}>
                  View summary analytics
                  <ArrowUpRight size={16} />
                </Button>
              </>
            ) : null}
          </div>
        </Card>
      </section>

      {user?.role === "ASSESSOR" ? (
        <Card title="Assigned assessments" subtitle="Your online and offline-ready assignments stay in one place.">
          <Table data={myAssessments.slice(0, 5)} columns={assessmentColumns} />
        </Card>
      ) : (
        <Card title="Recent reports" subtitle="Generated reports remain draft or generated until they are reviewed and approved.">
          <Table data={reports} columns={reportColumns} />
        </Card>
      )}

      {(user?.role === "MANAGER" || user?.role === "REVIEWER") && actions.length > 0 ? (
        <Card title="Corrective action focus" subtitle="Open and overdue actions stay visible so follow-up does not stall.">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl bg-brand-surface px-5 py-5">
              <p className="text-sm font-semibold text-brand-text">Open or in progress</p>
              <p className="mt-2 text-3xl font-bold text-brand-navy">
                {actions.filter((item) => item.status === "OPEN" || item.status === "IN_PROGRESS").length}
              </p>
            </div>
            <div className="rounded-2xl bg-brand-surface px-5 py-5">
              <p className="text-sm font-semibold text-brand-text">Overdue</p>
              <p className="mt-2 text-3xl font-bold text-brand-danger">
                {actions.filter((item) => item.status === "OVERDUE").length}
              </p>
            </div>
            <div className="rounded-2xl bg-brand-surface px-5 py-5">
              <p className="text-sm font-semibold text-brand-text">Verified</p>
              <p className="mt-2 text-3xl font-bold text-brand-teal">
                {actions.filter((item) => item.status === "VERIFIED").length}
              </p>
            </div>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
