import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { ArrowUpRight, ClipboardCheck, Download, FileSpreadsheet, Gauge, ShieldAlert } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Table } from "../components/ui/Table";
import { useAuth } from "../hooks/useAuth";
import { assessmentAssignmentService } from "../services/assessmentAssignmentService";
import { assessmentRoundService } from "../services/assessmentRoundService";
import { getPendingSyncCount, listCachedAssessments } from "../services/offlineStore";
import { submissionService } from "../services/submissionService";
import type { AssessmentRoundListItem, MyAssessmentListItem, SubmissionDashboard, SubmissionListItem } from "../types";

const assessmentColumns: ColumnDef<MyAssessmentListItem>[] = [
  { accessorKey: "facility_name", header: "Facility" },
  { accessorKey: "round_name", header: "Assessment" },
  { accessorKey: "reporting_period", header: "Period" },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <Badge tone={row.original.status === "SUBMITTED" ? "success" : "info"}>{row.original.status.replace(/_/g, " ")}</Badge>,
  },
];

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [rounds, setRounds] = useState<AssessmentRoundListItem[]>([]);
  const [selectedRoundId, setSelectedRoundId] = useState("");
  const [selectedTeamLeadId, setSelectedTeamLeadId] = useState("");
  const [submissions, setSubmissions] = useState<SubmissionDashboard | null>(null);
  const [myAssessments, setMyAssessments] = useState<MyAssessmentListItem[]>([]);
  const [pendingSyncCount, setPendingSyncCount] = useState(0);
  const [cachedCount, setCachedCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const selectedRound = useMemo(
    () => rounds.find((round) => round.id === selectedRoundId) ?? rounds[0] ?? null,
    [rounds, selectedRoundId],
  );

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (user?.role === "MANAGER" || user?.role === "REVIEWER") {
          const roundList = await assessmentRoundService.listRounds().catch(() => []);
          const nextRoundId = selectedRoundId || roundList[0]?.id || "";
          const submissionDashboard = await submissionService
            .getDashboard(nextRoundId || null, selectedTeamLeadId || null)
            .catch(() => null);
          setRounds(roundList);
          setSelectedRoundId(nextRoundId);
          setSubmissions(submissionDashboard);
        }
        if (user?.role === "ASSESSOR") {
          const [assigned, pending, cached] = await Promise.all([
            assessmentAssignmentService.listMyAssessments().catch(() => []),
            getPendingSyncCount().catch(() => 0),
            listCachedAssessments().catch(() => []),
          ]);
          setMyAssessments(assigned);
          setPendingSyncCount(pending);
          setCachedCount(cached.length);
        }
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [selectedRoundId, selectedTeamLeadId, user?.role]);

  if (user?.role === "ASSESSOR") {
    const submitted = myAssessments.filter((item) => item.status === "SUBMITTED").length;
    const active = myAssessments.length - submitted;
    return (
      <div className="space-y-6">
        <section className="rounded-[28px] bg-[radial-gradient(circle_at_top_right,rgba(26,173,136,.35),transparent_34%),linear-gradient(135deg,#152638,#0f1e2e_58%,#0a7a5e)] px-6 py-7 text-white shadow-panel">
          <p className="text-[10px] uppercase tracking-[0.32em] text-emerald-100">Assessment team dashboard</p>
          <h1 className="mt-2 font-display text-4xl font-semibold">Your assigned field work</h1>
          <p className="mt-2 max-w-2xl text-sm text-cyan-50/85">
            Open your assigned assessment, save locally as you work, sync when online, and Send to Manager when complete.
          </p>
        </section>
        <section className="grid gap-4 md:grid-cols-4">
          <Card className="metric-top-teal"><p className="text-sm text-brand-muted">Assigned</p><p className="mt-2 text-4xl font-black text-brand-navy">{myAssessments.length}</p></Card>
          <Card className="metric-top-teal"><p className="text-sm text-brand-muted">Active</p><p className="mt-2 text-4xl font-black text-brand-teal">{active}</p></Card>
          <Card className="metric-top-red"><p className="text-sm text-brand-muted">Pending sync</p><p className="mt-2 text-4xl font-black text-brand-danger">{pendingSyncCount}</p></Card>
          <Card className="metric-top-amber"><p className="text-sm text-brand-muted">Offline cached</p><p className="mt-2 text-4xl font-black text-brand-navy">{cachedCount}</p></Card>
        </section>
        <Card title="My assessments" subtitle="Only assessments assigned to your team appear here.">
          <div className="mb-4">
            <Button onClick={() => navigate("/my-assessments")}>Open My Assessments</Button>
          </div>
          <Table data={myAssessments.slice(0, 6)} columns={assessmentColumns} emptyMessage={loading ? "Loading..." : "No assigned assessments yet."} />
        </Card>
      </div>
    );
  }

  const stats = submissions?.stats;
  const recent = submissions?.submissions.slice(0, 6) ?? [];
  const recentColumns: ColumnDef<SubmissionListItem>[] = [
    {
      accessorKey: "facility_name",
      header: "Facility",
      cell: ({ row }) => (
        <div>
          <p className="font-semibold text-brand-text">{row.original.facility_name}</p>
          <p className="text-xs text-brand-muted">{row.original.team_lead ?? "No Team Lead"}</p>
        </div>
      ),
    },
    {
      accessorKey: "submitted_at",
      header: "Submitted",
      cell: ({ row }) => row.original.submitted_at ? new Date(row.original.submitted_at).toLocaleString() : "Pending",
    },
    {
      accessorKey: "dqa_score",
      header: "Score",
      cell: ({ row }) => `${row.original.dqa_score.toFixed(1)}%`,
    },
    {
      accessorKey: "flagged_rows",
      header: "Flags",
      cell: ({ row }) => <Badge tone={row.original.flagged_rows > 0 ? "danger" : "success"}>{row.original.flagged_rows} flagged</Badge>,
    },
    {
      id: "actions",
      header: "Action",
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" className="px-3 py-2 text-xs" onClick={() => navigate("/submissions")}>
            View data
          </Button>
          <Button
            className="px-3 py-2 text-xs"
            onClick={() => submissionService.downloadSubmissionXlsx(row.original.assessment_facility_id)}
          >
            Excel
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] bg-[radial-gradient(circle_at_top_right,rgba(26,173,136,.35),transparent_34%),linear-gradient(135deg,#152638,#0f1e2e_58%,#0a7a5e)] px-6 py-8 text-white shadow-panel">
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr] xl:items-end">
          <div>
            <p className="text-[10px] uppercase tracking-[0.32em] text-emerald-100">Manager dashboard</p>
            <h1 className="mt-3 font-display text-5xl font-semibold tracking-tight">Assessment monitoring, without the noise.</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-cyan-50/85">
              Select one assessment round, review submitted facility data, watch cumulative statistics, and download Excel files for follow-up.
            </p>
          </div>
          <div className="rounded-3xl border border-white/15 bg-white/10 p-4 backdrop-blur">
            <label className="text-sm font-semibold text-cyan-50">Assessment round</label>
            <select
              className="mt-2 w-full rounded-2xl border border-white/20 bg-white px-4 py-3 text-sm text-brand-navy outline-none"
              value={selectedRound?.id ?? ""}
              onChange={(event) => {
                setSelectedRoundId(event.target.value);
                setSelectedTeamLeadId("");
              }}
            >
              {rounds.length === 0 ? <option value="">No assessments yet</option> : null}
              {rounds.map((round) => (
                <option key={round.id} value={round.id}>
                  {round.assessment_code} - {round.name} - {round.reporting_period}
                </option>
              ))}
            </select>
            <label className="mt-4 block text-sm font-semibold text-cyan-50">Team Lead</label>
            <select
              className="mt-2 w-full rounded-2xl border border-white/20 bg-white px-4 py-3 text-sm text-brand-navy outline-none"
              value={selectedTeamLeadId}
              onChange={(event) => setSelectedTeamLeadId(event.target.value)}
            >
              <option value="">All Team Leads</option>
              {(submissions?.team_leads ?? []).map((lead) => (
                <option key={lead.user_id} value={lead.user_id}>
                  {lead.full_name}
                </option>
              ))}
            </select>
            <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/20">
              <div className="h-full rounded-full bg-cyan-300" style={{ width: `${stats?.completion_percent ?? 0}%` }} />
            </div>
            <p className="mt-2 text-xs text-cyan-50/80">
              {stats?.completion_percent.toFixed(1) ?? "0.0"}% complete · {stats?.remaining_percent.toFixed(1) ?? "100.0"}% remaining
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <Card className="metric-top-teal xl:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-brand-muted">Submitted facilities</p>
              <p className="mt-2 text-4xl font-black text-brand-navy">{stats?.submitted_facilities ?? "--"}/{stats?.total_facilities ?? "--"}</p>
            </div>
            <ClipboardCheck className="text-brand-teal" />
          </div>
        </Card>
        <Card className="metric-top-amber">
          <p className="text-sm text-brand-muted">Pending</p>
          <p className="mt-2 text-4xl font-black text-brand-navy">{stats?.pending_facilities ?? "--"}</p>
        </Card>
        <Card className="metric-top-teal">
          <p className="text-sm text-brand-muted">Rows</p>
          <p className="mt-2 text-4xl font-black text-brand-navy">{stats?.total_submitted_rows ?? "--"}</p>
        </Card>
        <Card className="metric-top-red">
          <p className="text-sm text-brand-muted">Flags</p>
          <p className="mt-2 text-4xl font-black text-brand-danger">{stats?.flagged_count ?? "--"}</p>
        </Card>
        <Card className="metric-top-purple">
          <p className="text-sm text-brand-muted">Avg score</p>
          <p className="mt-2 text-4xl font-black text-brand-teal">{stats ? stats.average_score_percent.toFixed(1) : "--"}%</p>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_0.75fr]">
        <Card title="What to do next" subtitle="The manager workflow is intentionally short.">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl bg-brand-surface p-4">
              <Gauge className="text-brand-teal" size={20} />
              <p className="mt-3 font-semibold text-brand-text">1. Monitor progress</p>
              <p className="mt-1 text-sm text-brand-muted">Select the assessment and check submitted, pending, and flagged counts.</p>
            </div>
            <div className="rounded-2xl bg-brand-surface p-4">
              <ShieldAlert className="text-brand-danger" size={20} />
              <p className="mt-3 font-semibold text-brand-text">2. Review flagged data</p>
              <p className="mt-1 text-sm text-brand-muted">Open Submissions to inspect facility values and refresh analysis.</p>
            </div>
            <div className="rounded-2xl bg-brand-surface p-4">
              <FileSpreadsheet className="text-brand-teal" size={20} />
              <p className="mt-3 font-semibold text-brand-text">3. Download evidence</p>
              <p className="mt-1 text-sm text-brand-muted">Download cumulative Excel or individual facility submissions.</p>
            </div>
          </div>
        </Card>

        <Card title="Actions" subtitle="Only the useful manager actions.">
          <div className="space-y-3">
            <Button className="w-full justify-between" onClick={() => navigate("/submissions")}>
              Open submissions
              <ArrowUpRight size={16} />
            </Button>
            <Button
              variant="secondary"
              className="w-full justify-between"
              onClick={() => submissionService.downloadCumulativeXlsx(selectedRound?.id ?? null, selectedTeamLeadId || null)}
            >
              Download cumulative Excel
              <Download size={16} />
            </Button>
            <Button variant="secondary" className="w-full justify-between" onClick={() => navigate("/assessment-rounds")}>
              Manage assessment setup
              <ArrowUpRight size={16} />
            </Button>
          </div>
        </Card>
      </section>

      <Card title="Recent submissions" subtitle="Submitted team data appears here immediately after Send to Manager.">
        <Table data={recent} columns={recentColumns} emptyMessage={loading ? "Loading submissions..." : "No submitted assessments yet."} />
      </Card>
    </div>
  );
}
