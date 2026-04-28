import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, Eye, PlayCircle, RefreshCcw } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Table } from "../components/ui/Table";
import { assessmentRoundService } from "../services/assessmentRoundService";
import { comparisonService } from "../services/comparisonService";
import { submissionService } from "../services/submissionService";
import type { AssessmentRoundListItem, SubmissionDashboard, SubmissionDetail, SubmissionListItem, SubmissionValueRow } from "../types";

function flagTone(flag: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (flag === "Match") return "success";
  if (flag === "Within 5%") return "warning";
  if (flag === "Critical" || flag === "Flagged >5%") return "danger";
  if (flag === "Incomplete") return "neutral";
  return "info";
}

export function SubmissionsPage() {
  const [rounds, setRounds] = useState<AssessmentRoundListItem[]>([]);
  const [selectedRoundId, setSelectedRoundId] = useState("");
  const [dashboard, setDashboard] = useState<SubmissionDashboard | null>(null);
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = async (roundId = selectedRoundId) => {
    setLoading(true);
    try {
      const [roundList, submissionDashboard] = await Promise.all([
        assessmentRoundService.listRounds(),
        submissionService.getDashboard(roundId || null),
      ]);
      setRounds(roundList);
      setDashboard(submissionDashboard);
      if (!roundId && roundList[0]?.id) {
        setSelectedRoundId(roundList[0].id);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load("");
  }, []);

  useEffect(() => {
    if (selectedRoundId) {
      void load(selectedRoundId);
    }
  }, [selectedRoundId]);

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
        header: "Team",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium text-brand-text">{row.original.team_lead ?? "No Team Lead"}</p>
            <p className="text-xs text-brand-muted">
              {row.original.team_members.length ? row.original.team_members.join(", ") : "Team Lead only"}
            </p>
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
          <div>
            <p className="font-semibold text-brand-navy">{row.original.dqa_score.toFixed(1)}%</p>
            <p className="text-xs text-brand-muted">{row.original.score_category}</p>
          </div>
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
              View
            </Button>
            <Button
              variant="secondary"
              className="px-3 py-2 text-xs"
              onClick={async () => {
                setRunningId(row.original.assessment_facility_id);
                await comparisonService.runAssessmentFacilityComparison(row.original.assessment_facility_id);
                await load(selectedRoundId);
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
    [runningId, selectedRoundId],
  );

  const valueColumns = useMemo<ColumnDef<SubmissionValueRow>[]>(
    () => [
      {
        accessorKey: "indicator_name",
        header: "Indicator",
        cell: ({ row }) => (
          <div>
            <p className="font-semibold text-brand-text">{row.original.indicator_name}</p>
            <p className="text-xs text-brand-muted">{row.original.hmis_code}</p>
          </div>
        ),
      },
      { accessorKey: "source_register", header: "Source" },
      { accessorKey: "register_value", header: "Register" },
      { accessorKey: "hmis105_value", header: "HMIS 105" },
      { accessorKey: "dhis2_value_at_assessment", header: "DHIS2" },
      {
        accessorKey: "discrepancy_percent",
        header: "% Diff",
        cell: ({ row }) => row.original.discrepancy_percent === null ? "N/A" : `${row.original.discrepancy_percent.toFixed(1)}%`,
      },
      {
        accessorKey: "flag",
        header: "Flag",
        cell: ({ row }) => <Badge tone={flagTone(row.original.flag)}>{row.original.flag}</Badge>,
      },
      { accessorKey: "issue_type", header: "Issue" },
    ],
    [],
  );

  const stats = dashboard?.stats;

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-brand-navy via-slate-900 to-brand-teal px-6 py-7 text-white shadow-panel">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-cyan-200">Manager submissions</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight">Submitted assessment data</h1>
            <p className="mt-2 max-w-3xl text-sm text-cyan-50/85">
              Review what field teams sent, refresh analysis, and download facility-level or cumulative Excel files from one place.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              className="bg-white/10 text-white hover:bg-white/20"
              onClick={() => void load(selectedRoundId)}
            >
              <RefreshCcw size={16} />
              Refresh
            </Button>
            <Button
              className="bg-white text-brand-navy hover:bg-cyan-50"
              onClick={() => submissionService.downloadCumulativeXlsx(selectedRoundId || null)}
            >
              <Download size={16} />
              Download cumulative Excel
            </Button>
          </div>
        </div>
      </section>

      <Card title="Assessment filter" subtitle="Select one assessment round to focus submissions and cumulative statistics.">
        <select
          className="w-full rounded-2xl border border-brand-border px-4 py-3 text-sm outline-none focus:border-brand-teal focus:ring-2 focus:ring-brand-teal/20"
          value={selectedRoundId}
          onChange={(event) => {
            setSelectedRoundId(event.target.value);
            setDetail(null);
          }}
        >
          <option value="">All assessment rounds</option>
          {rounds.map((round) => (
            <option key={round.id} value={round.id}>
              {round.name} - {round.reporting_period} - {round.status}
            </option>
          ))}
        </select>
      </Card>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="bg-white">
          <p className="text-sm text-brand-muted">Completion</p>
          <p className="mt-2 text-4xl font-black text-brand-navy">{stats ? stats.completion_percent.toFixed(1) : "--"}%</p>
          <p className="mt-2 text-sm text-brand-muted">{stats?.submitted_facilities ?? 0} submitted of {stats?.total_facilities ?? 0}</p>
        </Card>
        <Card className="bg-white">
          <p className="text-sm text-brand-muted">Submitted data rows</p>
          <p className="mt-2 text-4xl font-black text-brand-navy">{stats?.total_submitted_rows ?? "--"}</p>
          <p className="mt-2 text-sm text-brand-muted">Register, HMIS 105, and DHIS2 rows received</p>
        </Card>
        <Card className="bg-white">
          <p className="text-sm text-brand-muted">Flagged rows</p>
          <p className="mt-2 text-4xl font-black text-brand-danger">{stats?.flagged_count ?? "--"}</p>
          <p className="mt-2 text-sm text-brand-muted">{stats?.critical_count ?? 0} critical</p>
        </Card>
        <Card className="bg-white">
          <p className="text-sm text-brand-muted">Average DQA score</p>
          <p className="mt-2 text-4xl font-black text-brand-teal">{stats ? stats.average_score_percent.toFixed(1) : "--"}%</p>
          <p className="mt-2 text-sm text-brand-muted">{stats?.exact_count ?? 0} exact matches</p>
        </Card>
      </section>

      {message ? <p className="text-sm font-semibold text-brand-teal">{message}</p> : null}

      <Card title="Submitted assessments" subtitle="Only assessments sent to the manager appear here.">
        <Table
          data={dashboard?.submissions ?? []}
          columns={submissionColumns}
          emptyMessage={loading ? "Loading submissions..." : "No submitted assessments yet."}
        />
      </Card>

      {detail ? (
        <Card
          title={`${detail.summary.facility_name} submitted data`}
          subtitle={`Team Lead: ${detail.summary.team_lead ?? "Not set"} · ${detail.summary.completed_indicators}/${detail.summary.total_indicators} indicators completed`}
        >
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              <Badge tone="info">{detail.summary.score_category}</Badge>
              <Badge tone={detail.summary.flagged_rows > 0 ? "danger" : "success"}>{detail.summary.flagged_rows} flagged</Badge>
              {detail.summary.general_assessment_comment ? (
                <Badge tone="neutral">Comment included</Badge>
              ) : null}
            </div>
            <Button onClick={() => submissionService.downloadSubmissionXlsx(detail.summary.assessment_facility_id)}>
              <Download size={16} />
              Download this submission
            </Button>
          </div>
          {detail.summary.general_assessment_comment ? (
            <div className="mb-4 rounded-2xl bg-brand-surface px-4 py-3 text-sm text-brand-muted">
              {detail.summary.general_assessment_comment}
            </div>
          ) : null}
          <Table data={detail.values} columns={valueColumns} />
        </Card>
      ) : null}
    </div>
  );
}
