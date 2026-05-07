import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, Eye, FileText, PlayCircle, RefreshCcw, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Table } from "../components/ui/Table";
import { ScoreBreakdownModal } from "../components/submissions/ScoreBreakdownModal";
import { assessmentRoundService } from "../services/assessmentRoundService";
import { comparisonService } from "../services/comparisonService";
import { exportService } from "../services/exportService";
import { reportService } from "../services/reportService";
import { submissionService } from "../services/submissionService";
import type {
  AssessmentRoundListItem,
  SubmissionDashboard,
  SubmissionDetail,
  SubmissionListItem,
  SubmissionValueRow,
} from "../types";

function flagTone(flag: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (flag === "Match") return "success";
  if (flag === "Within 5%") return "warning";
  if (flag === "Critical" || flag === "Flagged >5%") return "danger";
  if (flag === "Incomplete") return "neutral";
  return "info";
}

function pct(referenceValue: number | null, comparisonValue: number | null) {
  if (referenceValue === null || comparisonValue === null) return null;
  if (referenceValue === 0 && comparisonValue === 0) return 0;
  if (referenceValue === 0) return null;
  return Math.abs(comparisonValue - referenceValue) / Math.abs(referenceValue) * 100;
}

function formatPct(value: number | null) {
  return value === null ? "N/A" : `${value.toFixed(1)}%`;
}

function DiffPill({ value }: { value: number | null }) {
  const tone = value === null ? "neutral" : value > 5 ? "danger" : value === 0 ? "success" : "warning";
  return <Badge tone={tone} className="font-mono-ui">{formatPct(value)}</Badge>;
}

async function extractReportErrorMessage(error: unknown): Promise<string> {
  const candidate = error as { response?: { data?: Blob | { detail?: string } } };
  const payload = candidate.response?.data;
  if (payload instanceof Blob) {
    try {
      const text = await payload.text();
      const parsed = JSON.parse(text) as { detail?: string };
      return parsed.detail ?? "The report could not be generated or downloaded.";
    } catch {
      return "The report could not be generated or downloaded.";
    }
  }
  if (payload && typeof payload === "object" && "detail" in payload) {
    return String(payload.detail ?? "The report could not be generated or downloaded.");
  }
  return "The report could not be generated or downloaded.";
}

export function SubmissionsPage() {
  const navigate = useNavigate();
  const [rounds, setRounds] = useState<AssessmentRoundListItem[]>([]);
  const [selectedRoundId, setSelectedRoundId] = useState("");
  const [selectedTeamLeadId, setSelectedTeamLeadId] = useState("");
  const [selectedFacilityId, setSelectedFacilityId] = useState("");
  const [dashboard, setDashboard] = useState<SubmissionDashboard | null>(null);
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [breakdown, setBreakdown] = useState<SubmissionDetail | null>(null);
  const [cumulativeDetails, setCumulativeDetails] = useState<SubmissionDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = async (roundId = selectedRoundId, teamLeadId = selectedTeamLeadId) => {
    setLoading(true);
    try {
      const [roundList, submissionDashboard] = await Promise.all([
        assessmentRoundService.listRounds(),
        submissionService.getDashboard(roundId || null, teamLeadId || null),
      ]);
      setRounds(roundList);
      setDashboard(submissionDashboard);
      const detailRows = await Promise.all(
        submissionDashboard.submissions
          .filter((item) => item.completed_indicators > 0)
          .slice(0, 25)
          .map((item) => submissionService.getSubmission(item.assessment_facility_id).catch(() => null)),
      );
      setCumulativeDetails(detailRows.filter((item): item is SubmissionDetail => Boolean(item)));
      setMessage(null);
    } catch {
      setDashboard(null);
      setCumulativeDetails([]);
      setMessage("Unable to load submissions right now. If your session expired, please sign in again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(selectedRoundId, selectedTeamLeadId);
  }, [selectedRoundId, selectedTeamLeadId]);

  const submissionColumns = useMemo<ColumnDef<SubmissionListItem>[]>(
    () => [
      {
        accessorKey: "facility_name",
        header: "Facility",
        cell: ({ row }) => (
          <div>
            <p className="font-semibold text-brand-text">{row.original.facility_name}</p>
            <p className="text-xs text-brand-muted">{row.original.district}</p>
          </div>
        ),
      },
      {
        accessorKey: "team_lead",
        header: "Group account",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium text-brand-text">{row.original.team_lead ?? "No group account assigned"}</p>
            <p className="text-xs text-brand-muted">Used by all members of that assigned group.</p>
          </div>
        ),
      },
      {
        accessorKey: "submitted_at",
        header: "Submitted",
        cell: ({ row }) =>
          row.original.submitted_at ? new Date(row.original.submitted_at).toLocaleString() : "Not submitted",
      },
      {
        accessorKey: "completed_indicators",
        header: "Values",
        cell: ({ row }) => `${row.original.completed_indicators}/${row.original.total_indicators}`,
      },
      {
        accessorKey: "dqa_score",
        header: "Score",
        cell: ({ row }) => (
          <button
            type="button"
            title="Click to see how this score was calculated"
            className="flex h-12 w-12 items-center justify-center rounded-full border-[3px] border-brand-teal bg-emerald-50 transition hover:bg-emerald-100 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2"
            onClick={async () => {
              const fresh = await submissionService.getSubmission(row.original.assessment_facility_id);
              setBreakdown(fresh);
            }}
          >
            <span className="font-mono-ui text-xs font-semibold text-brand-navy">{row.original.dqa_score.toFixed(0)}%</span>
          </button>
        ),
      },
      {
        accessorKey: "flagged_rows",
        header: "Flags",
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-2">
            <Badge tone={row.original.flagged_rows > 0 ? "danger" : "success"}>{row.original.flagged_rows} flagged</Badge>
            {row.original.critical_rows > 0 ? <Badge tone="danger">{row.original.critical_rows} critical</Badge> : null}
          </div>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              className="px-3 py-2 text-xs"
              onClick={async () => setDetail(await submissionService.getSubmission(row.original.assessment_facility_id))}
            >
              <Eye size={14} />
              Review
            </Button>
            <Button
              variant="secondary"
              className="px-3 py-2 text-xs"
              onClick={async () => {
                setRunningId(row.original.assessment_facility_id);
                await comparisonService.runAssessmentFacilityComparison(row.original.assessment_facility_id);
                await load(selectedRoundId, selectedTeamLeadId);
                setMessage("Analysis refreshed.");
                setRunningId(null);
              }}
            >
              <PlayCircle size={14} />
              {runningId === row.original.assessment_facility_id ? "Running" : "Analyze"}
            </Button>
            <Button
              className="px-3 py-2 text-xs"
              onClick={() => submissionService.downloadSubmissionXlsx(row.original.assessment_facility_id)}
            >
              <Download size={14} />
              Excel
            </Button>
          </div>
        ),
      },
    ],
    [runningId, selectedRoundId, selectedTeamLeadId],
  );

  const valueColumns = useMemo<ColumnDef<SubmissionValueRow>[]>(
    () => [
      {
        accessorKey: "indicator_name",
        header: "Indicator",
        cell: ({ row }) => (
          <div>
            <p className="font-semibold text-brand-text">{row.original.indicator_name}</p>
            <p className="font-mono-ui text-xs text-brand-teal">{row.original.hmis_code}</p>
          </div>
        ),
      },
      { accessorKey: "source_register", header: "Source" },
      { accessorKey: "register_value", header: "Register" },
      { accessorKey: "hmis105_value", header: "HMIS 105" },
      {
        accessorKey: "dhis2_value_at_assessment",
        header: "DHIS2",
        cell: ({ row }) => (
          <span className="font-mono-ui rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-semibold text-emerald-700">
            {row.original.dhis2_value_at_assessment ?? "-"}
          </span>
        ),
      },
      {
        id: "hmis_reg",
        header: "HMIS / Reg",
        cell: ({ row }) => <DiffPill value={pct(row.original.register_value, row.original.hmis105_value)} />,
      },
      {
        id: "dhis_hmis",
        header: "DHIS2 / HMIS",
        cell: ({ row }) => <DiffPill value={pct(row.original.hmis105_value, row.original.dhis2_value_at_assessment)} />,
      },
      {
        id: "dhis_reg",
        header: "DHIS2 / Reg",
        cell: ({ row }) => <DiffPill value={pct(row.original.register_value, row.original.dhis2_value_at_assessment)} />,
      },
      {
        accessorKey: "flag",
        header: "Flag",
        cell: ({ row }) => <Badge tone={flagTone(row.original.flag)}>{row.original.flag}</Badge>,
      },
    ],
    [],
  );

  const stats = dashboard?.stats;
  const visibleCumulativeDetails = selectedFacilityId
    ? cumulativeDetails.filter((submission) => submission.summary.assessment_facility_id === selectedFacilityId)
    : cumulativeDetails;
  const cumulativeRows = visibleCumulativeDetails.flatMap((submission) =>
    submission.values.map((value) => ({
      submission,
      value,
      hmisReg: pct(value.register_value, value.hmis105_value),
      dhisHmis: pct(value.hmis105_value, value.dhis2_value_at_assessment),
      dhisReg: pct(value.register_value, value.dhis2_value_at_assessment),
    })),
  );
  const selectedRound = rounds.find((round) => round.id === selectedRoundId) ?? null;
  const selectedTeamLead = dashboard?.team_leads.find((lead) => lead.user_id === selectedTeamLeadId) ?? null;
  const facilityOptions = dashboard?.submissions ?? [];
  const canGenerateReport = (dashboard?.submissions.length ?? 0) > 0;
  const reportScopeLabel = selectedRound
    ? selectedTeamLead
      ? `${selectedRound.assessment_code} - ${selectedRound.name}; ${selectedTeamLead.full_name}`
      : `${selectedRound.assessment_code} - ${selectedRound.name}`
    : selectedTeamLead
      ? `All submissions for ${selectedTeamLead.full_name}`
      : "All submitted assessments";

  const handleGenerateReport = async (downloadDocx = false) => {
    if (!canGenerateReport) {
      setMessage("There are no submitted assessments in the selected scope yet.");
      return;
    }
    setGeneratingReport(true);
    setMessage(null);
    try {
      const report = await reportService.generateReport({
        assessment_round_id: selectedRoundId || null,
        assessment_facility_id: null,
        team_lead_user_id: selectedTeamLeadId || null,
        report_type: "CONSOLIDATED_UCMB_DQA_REPORT",
        include_comments: true,
      });
      setMessage(downloadDocx ? "Report generated. Opening Word download..." : "Report generated. Opening report review page...");
      if (downloadDocx) {
        await exportService.downloadDocx(report.id);
        setMessage("Word report generated and download started.");
      } else {
        navigate(`/reports/${report.id}`);
      }
    } catch (error) {
      setMessage(await extractReportErrorMessage(error));
    } finally {
      setGeneratingReport(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] bg-[radial-gradient(circle_at_top_right,rgba(26,173,136,.35),transparent_34%),linear-gradient(135deg,#152638,#0f1e2e_58%,#0a7a5e)] px-6 py-7 text-white shadow-panel">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-[0.32em] text-emerald-100">Manager submissions</p>
            <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight">Submitted assessment data</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-white/78">
              Review what field teams sent, refresh analysis, and download facility-level or cumulative Excel files from one place.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              className="border-white/15 bg-white/10 text-white hover:bg-white/20"
              onClick={() => void load(selectedRoundId)}
            >
              <RefreshCcw size={16} />
              Refresh
            </Button>
            <Button
              className="bg-white text-brand-navy hover:bg-cyan-50"
              onClick={() => submissionService.downloadCumulativeXlsx(selectedRoundId || null, selectedTeamLeadId || null, selectedFacilityId || null)}
            >
              <Download size={16} />
              Download cumulative Excel
            </Button>
          </div>
        </div>
      </section>

      <Card
        title="Generate full consolidated report"
        subtitle="Generate one consolidated report from live submitted data. Comments are included automatically."
      >
        <div className="grid gap-4 xl:grid-cols-[1fr_auto] xl:items-end">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-brand-border bg-brand-surface px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">Report scope</p>
              <p className="mt-1 text-sm font-semibold text-brand-text">
                {reportScopeLabel}
              </p>
            </div>
            <div className="rounded-2xl border border-brand-border bg-white px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">Report format</p>
              <p className="mt-1 text-sm font-semibold text-brand-text">Full consolidated report</p>
            </div>
            <div className="rounded-2xl border border-brand-border bg-white px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">Comments</p>
              <p className="mt-1 text-sm font-semibold text-brand-text">Included automatically</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              className="gap-2"
              disabled={!canGenerateReport || generatingReport}
              onClick={() => void handleGenerateReport(false)}
            >
              <Eye size={16} />
              {generatingReport ? "Generating..." : "Generate and review"}
            </Button>
            <Button
              className="gap-2"
              disabled={!canGenerateReport || generatingReport}
              onClick={() => void handleGenerateReport(true)}
            >
              <FileText size={16} />
              Generate Word report
            </Button>
          </div>
        </div>
      </Card>

      <Card title="Filter submissions" subtitle="Each facility is tied to one shared group account. Select a group account to view only that group's facilities and statistics.">
        <div className="grid gap-4 lg:grid-cols-3">
          <label>
            <span className="mb-2 block text-sm font-semibold text-brand-text">Assessment round</span>
            <select
              className="w-full rounded-2xl border border-brand-border px-4 py-3 text-sm outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20"
              value={selectedRoundId}
              onChange={(event) => {
                setSelectedRoundId(event.target.value);
                setSelectedTeamLeadId("");
                setSelectedFacilityId("");
                setDetail(null);
              }}
            >
              <option value="">All assessment rounds</option>
              {rounds.map((round) => (
                <option key={round.id} value={round.id}>
                  {round.assessment_code} - {round.name} - {round.reporting_period} - {round.status}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-2 block text-sm font-semibold text-brand-text">Group account</span>
            <select
              className="w-full rounded-2xl border border-brand-border px-4 py-3 text-sm outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20"
              value={selectedTeamLeadId}
              onChange={(event) => {
                setSelectedTeamLeadId(event.target.value);
                setSelectedFacilityId("");
                setDetail(null);
              }}
            >
              <option value="">All group accounts</option>
              {(dashboard?.team_leads ?? []).map((lead) => (
                <option key={lead.user_id} value={lead.user_id}>
                  {lead.full_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-2 block text-sm font-semibold text-brand-text">Facility</span>
            <select
              className="w-full rounded-2xl border border-brand-border px-4 py-3 text-sm outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20"
              value={selectedFacilityId}
              onChange={(event) => {
                setSelectedFacilityId(event.target.value);
                setDetail(null);
              }}
            >
              <option value="">All visible facilities</option>
              {facilityOptions.map((submission) => (
                <option key={submission.assessment_facility_id} value={submission.assessment_facility_id}>
                  {submission.facility_name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="metric-top-teal bg-white">
          <p className="text-sm text-brand-muted">Completion</p>
          <p className="mt-2 text-4xl font-black text-brand-navy">{stats ? stats.completion_percent.toFixed(1) : "--"}%</p>
          <p className="mt-2 text-sm text-brand-muted">{stats?.submitted_facilities ?? 0} submitted of {stats?.total_facilities ?? 0}</p>
        </Card>
        <Card className="metric-top-teal bg-white">
          <p className="text-sm text-brand-muted">Submitted data rows</p>
          <p className="mt-2 text-4xl font-black text-brand-navy">{stats?.total_submitted_rows ?? "--"}</p>
          <p className="mt-2 text-sm text-brand-muted">Register, HMIS 105, and DHIS2 rows received</p>
        </Card>
        <Card className="metric-top-red bg-white">
          <p className="text-sm text-brand-muted">Flagged rows</p>
          <p className="mt-2 text-4xl font-black text-brand-danger">{stats?.flagged_count ?? "--"}</p>
          <p className="mt-2 text-sm text-brand-muted">{stats?.critical_count ?? 0} critical</p>
        </Card>
        <Card className="metric-top-purple bg-white">
          <p className="text-sm text-brand-muted">Average DQA score</p>
          <p className="mt-2 text-4xl font-black text-brand-teal">{stats ? stats.average_score_percent.toFixed(1) : "--"}%</p>
          <p className="mt-2 text-sm text-brand-muted">{stats?.exact_count ?? 0} exact matches</p>
        </Card>
      </section>

      {message ? <p className="text-sm font-semibold text-brand-teal">{message}</p> : null}

      <Card title="Submitted assessments" subtitle="Only assessments sent to the manager appear here.">
        <Table
          data={(dashboard?.submissions ?? []).filter((item) => !selectedFacilityId || item.assessment_facility_id === selectedFacilityId)}
          columns={submissionColumns}
          emptyMessage={loading ? "Loading submissions..." : "No submitted assessments yet."}
        />
      </Card>

      <Card
        title="Cumulative data grid"
        subtitle="All submitted facility rows in one manager view. Use Excel export for the full workbook."
      >
        <div className="overflow-x-auto rounded-[18px] border border-brand-border">
          <table className="min-w-[1120px] divide-y divide-brand-border/70 bg-white">
            <thead>
              <tr className="bg-brand-blue text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-white/80">
                <th className="px-4 py-3">Facility</th>
                <th className="px-4 py-3">Indicator</th>
                <th className="px-4 py-3">Code</th>
                <th className="bg-emerald-950/40 px-4 py-3">Register</th>
                <th className="bg-sky-950/40 px-4 py-3">HMIS 105</th>
                <th className="border-l-2 border-white/70 bg-emerald-900 px-4 py-3">DHIS2</th>
                <th className="bg-amber-950/50 px-4 py-3">HMIS / Reg</th>
                <th className="bg-blue-950/50 px-4 py-3">DHIS2 / HMIS</th>
                <th className="bg-emerald-950/50 px-4 py-3">DHIS2 / Reg</th>
                <th className="bg-purple-950/60 px-4 py-3">Flag</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border/70">
              {cumulativeRows.length > 0 ? cumulativeRows.map(({ submission, value, hmisReg, dhisHmis, dhisReg }) => (
                <tr key={`${submission.summary.assessment_facility_id}-${value.indicator_id}`} className="hover:bg-brand-surface/70">
                  <td className="px-4 py-3 text-sm font-semibold text-brand-text">{submission.summary.facility_name}</td>
                  <td className="max-w-xs px-4 py-3 text-sm text-brand-text">{value.indicator_name}</td>
                  <td className="font-mono-ui px-4 py-3 text-sm text-brand-teal">{value.hmis_code}</td>
                  <td className="font-mono-ui px-4 py-3 text-sm">{value.register_value ?? "-"}</td>
                  <td className="font-mono-ui px-4 py-3 text-sm">{value.hmis105_value ?? "-"}</td>
                  <td className="font-mono-ui border-l-2 border-emerald-200 bg-emerald-50/50 px-4 py-3 text-sm font-semibold text-emerald-700">
                    {value.dhis2_value_at_assessment ?? "-"}
                  </td>
                  <td className="px-4 py-3"><DiffPill value={hmisReg} /></td>
                  <td className="px-4 py-3"><DiffPill value={dhisHmis} /></td>
                  <td className="px-4 py-3"><DiffPill value={dhisReg} /></td>
                  <td className="px-4 py-3"><Badge tone={flagTone(value.flag)}>{value.flag}</Badge></td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={10} className="px-4 py-8 text-center text-sm text-brand-muted">
                    No submitted values are available for the selected filters yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {breakdown ? (
        <ScoreBreakdownModal detail={breakdown} onClose={() => setBreakdown(null)} />
      ) : null}

      {detail ? (
        <div className="fixed inset-0 z-40 bg-brand-navy/55 backdrop-blur-sm" onClick={() => setDetail(null)}>
          <aside
            className="ml-auto h-full w-full max-w-5xl overflow-y-auto bg-white shadow-panel"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="sticky top-0 z-10 flex items-center justify-between gap-4 bg-brand-navy px-6 py-4 text-white">
              <div>
                <h2 className="font-display text-2xl font-semibold">Reviewing: {detail.summary.facility_name}</h2>
                <p className="mt-1 text-sm text-white/65">
                  {detail.summary.team_lead ?? "No group account assigned"} - {detail.summary.completed_indicators}/{detail.summary.total_indicators} indicators completed
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  className="bg-white text-brand-navy hover:bg-emerald-50"
                  onClick={() => submissionService.downloadSubmissionXlsx(detail.summary.assessment_facility_id)}
                >
                  <Download size={16} />
                  Excel
                </Button>
                <Button variant="ghost" className="text-white hover:bg-white/10" onClick={() => setDetail(null)}>
                  <X size={18} />
                </Button>
              </div>
            </div>
            <div className="space-y-5 p-6">
              <section className="grid gap-3 md:grid-cols-4">
                <button
                  type="button"
                  className="metric-card metric-top-teal text-left transition hover:shadow-panel focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2"
                  onClick={() => setBreakdown(detail)}
                  title="Click to see how this score was calculated"
                >
                  <span className="block text-sm text-brand-muted">DQA score</span>
                  <span className="mt-2 block text-3xl font-black text-brand-teal">{detail.summary.dqa_score.toFixed(1)}%</span>
                  <span className="mt-1 block text-[10px] font-semibold uppercase tracking-[0.18em] text-brand-teal">Click to explain</span>
                </button>
                <div className="metric-card metric-top-red">
                  <p className="text-sm text-brand-muted">Flagged rows</p>
                  <p className="mt-2 text-3xl font-black text-brand-danger">{detail.summary.flagged_rows}</p>
                </div>
                <div className="metric-card metric-top-amber">
                  <p className="text-sm text-brand-muted">Status</p>
                  <p className="mt-2 text-lg font-bold text-brand-text">{detail.summary.status.replace(/_/g, " ")}</p>
                </div>
                <div className="metric-card metric-top-purple">
                  <p className="text-sm text-brand-muted">Category</p>
                  <p className="mt-2 text-lg font-bold text-brand-text">{detail.summary.score_category}</p>
                </div>
              </section>
              {detail.summary.general_assessment_comment ? (
                <div className="rounded-[18px] border border-brand-border bg-brand-surface px-4 py-3 text-sm text-brand-muted">
                  {detail.summary.general_assessment_comment}
                </div>
              ) : null}
              <Card title="Assessment values and three-way differences">
                <Table data={detail.values} columns={valueColumns} />
              </Card>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
