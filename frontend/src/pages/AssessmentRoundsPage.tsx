import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { ArrowRight, CalendarRange, ClipboardList, PlusCircle, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Table } from "../components/ui/Table";
import { useAuth } from "../hooks/useAuth";
import { assessmentRoundService } from "../services/assessmentRoundService";
import type { AssessmentRoundListItem } from "../types";

const statusTone: Record<
  AssessmentRoundListItem["status"],
  "neutral" | "success" | "warning" | "danger" | "info"
> = {
  DRAFT: "warning",
  PUBLISHED: "success",
  IN_PROGRESS: "info",
  CLOSED: "neutral",
  ARCHIVED: "neutral",
};

export function AssessmentRoundsPage() {
  const { user } = useAuth();
  const [rounds, setRounds] = useState<AssessmentRoundListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadRounds = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await assessmentRoundService.listRounds();
      setRounds(data);
    } catch {
      setError("Unable to load assessment rounds right now.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRounds();
  }, [loadRounds]);

  const assessmentSections = useMemo(() => {
    const grouped = rounds.reduce<Map<string, AssessmentRoundListItem[]>>((accumulator, round) => {
      const key = round.name.trim() || "Unnamed assessment";
      const items = accumulator.get(key) ?? [];
      items.push(round);
      accumulator.set(key, items);
      return accumulator;
    }, new Map());

    return Array.from(grouped.entries())
      .map(([name, items]) => ({
        name,
        rounds: items.sort((left, right) => right.created_at.localeCompare(left.created_at)),
        facilityCount: items.reduce((total, item) => total + item.facility_count, 0),
        assignedFacilityCount: items.reduce((total, item) => total + item.assigned_facility_count, 0),
      }))
      .sort((left, right) => right.rounds[0].created_at.localeCompare(left.rounds[0].created_at));
  }, [rounds]);

  const deleteRound = useCallback(async (round: AssessmentRoundListItem) => {
    const confirmed = window.confirm(
      `Delete "${round.name}" and all of its assessment assignments? This cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingId(round.id);
    setError(null);
    try {
      await assessmentRoundService.deleteRound(round.id);
      setRounds((current) => current.filter((item) => item.id !== round.id));
    } catch {
      setError("Unable to delete this assessment round. Please try again.");
    } finally {
      setDeletingId(null);
    }
  }, []);

  const columns = useMemo<ColumnDef<AssessmentRoundListItem>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Round",
        cell: ({ row }) => (
          <div>
            <p className="font-semibold text-brand-text">{row.original.name}</p>
            <p className="mt-1 text-xs font-semibold text-brand-teal">{row.original.assessment_code}</p>
            <p className="mt-1 text-xs text-brand-muted">{row.original.description ?? "No description"}</p>
          </div>
        ),
      },
      {
        accessorKey: "reporting_period",
        header: "Period",
        cell: ({ row }) => (
          <div className="text-sm">
            <p className="font-medium text-brand-text">{row.original.reporting_period}</p>
            <p className="text-xs text-brand-muted">
              {row.original.start_date && row.original.end_date
                ? `DHIS2 months: ${row.original.start_date.slice(0, 7)} to ${row.original.end_date.slice(0, 7)}`
                : "DHIS2 month range not set"}
            </p>
          </div>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => <Badge tone={statusTone[row.original.status]}>{row.original.status}</Badge>,
      },
      {
        accessorKey: "facility_count",
        header: "Facilities",
        cell: ({ row }) => (
          <div className="text-sm text-brand-text">
            {row.original.facility_count} selected
            <p className="text-xs text-brand-muted">{row.original.assigned_facility_count} assigned</p>
          </div>
        ),
      },
      {
        accessorKey: "indicator_count",
        header: "Indicators",
      },
      {
        accessorKey: "deadline",
        header: "Deadline",
        cell: ({ row }) => row.original.deadline ?? "No deadline",
      },
      {
        accessorKey: "completion_percent",
        header: "Progress",
        cell: ({ row }) => `${row.original.completion_percent}%`,
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="flex flex-wrap items-center gap-3">
            <Link className="text-sm font-semibold text-brand-teal" to={`/assessment-rounds/${row.original.id}`}>
              {user?.role === "MANAGER" ? "Edit assessment" : "View"}
            </Link>
            {user?.role === "MANAGER" ? (
              <button
                type="button"
                className="inline-flex items-center gap-1 text-sm font-semibold text-brand-danger disabled:cursor-not-allowed disabled:opacity-60"
                disabled={deletingId === row.original.id}
                onClick={() => void deleteRound(row.original)}
              >
                <Trash2 size={14} />
                {deletingId === row.original.id ? "Deleting..." : "Delete"}
              </button>
            ) : null}
          </div>
        ),
      },
    ],
    [deleteRound, deletingId, user?.role],
  );

  return (
    <div className="space-y-6">
      <Card
        title="Assessment Rounds"
        subtitle="Managers build round packages by selecting indicators, facilities, assessors, and deadlines."
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-3">
            <Badge tone="info" className="gap-1">
              <ClipboardList size={14} />
              Manager-selected indicators
            </Badge>
            <Badge tone="success" className="gap-1">
              <CalendarRange size={14} />
              Offline-ready package structure
            </Badge>
          </div>
          {user?.role === "MANAGER" ? (
            <Link to="/assessment-rounds/new">
              <Button className="gap-2">
                <PlusCircle size={16} />
                Create assessment round
              </Button>
            </Link>
          ) : null}
        </div>
      </Card>

      {error ? <p className="text-sm text-brand-danger">{error}</p> : null}

      {loading ? (
        <Card>
          <div className="rounded-2xl border border-brand-border bg-brand-surface p-6 text-sm text-brand-muted">
            Loading assessment rounds...
          </div>
        </Card>
      ) : rounds.length === 0 ? (
        <Card title="No assessment rounds yet" subtitle="Managers can create the first round from the builder.">
          {user?.role === "MANAGER" ? (
            <Link to="/assessment-rounds/new" className="inline-flex items-center gap-2 text-sm font-semibold text-brand-teal">
              Open the builder
              <ArrowRight size={16} />
            </Link>
          ) : (
            <p className="text-sm text-brand-muted">Published rounds will appear here once they are created.</p>
          )}
        </Card>
      ) : (
        <>
          <Card
            title="Assessment activity sections"
            subtitle="Each section groups batches that share the same assessment activity. Open a batch to add teams, change facilities, sync DHIS2, or generate reports for that specific assessment."
          >
            <div className="grid gap-4 lg:grid-cols-2">
              {assessmentSections.map((section) => {
                const latestRound = section.rounds[0];
                return (
                  <div key={section.name} className="rounded-2xl border border-brand-border bg-brand-surface p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-brand-text">{section.name}</p>
                        <p className="mt-1 text-xs text-brand-muted">
                          {section.rounds.length} assessment batch{section.rounds.length === 1 ? "" : "es"} · {section.facilityCount} facilities · {section.assignedFacilityCount} assigned
                        </p>
                      </div>
                      <Badge tone={statusTone[latestRound.status]}>{latestRound.status}</Badge>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Link className="rounded-xl bg-white px-3 py-2 text-xs font-semibold text-brand-teal shadow-sm" to={`/assessment-rounds/${latestRound.id}`}>
                        Open latest batch
                      </Link>
                      <Link
                        className="rounded-xl bg-white px-3 py-2 text-xs font-semibold text-brand-navy shadow-sm"
                        to={`/assessment-rounds/new?template=${latestRound.id}`}
                      >
                        Add another team/facility batch
                      </Link>
                    </div>
                    <div className="mt-4 space-y-2">
                      {section.rounds.slice(0, 3).map((round) => (
                        <Link
                          key={round.id}
                          className="block rounded-xl border border-white bg-white px-3 py-2 text-xs text-brand-muted"
                          to={`/assessment-rounds/${round.id}`}
                        >
                          <span className="font-semibold text-brand-text">{round.assessment_code}</span> - {round.reporting_period} - {round.facility_count} facilities
                        </Link>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
          <Table data={rounds} columns={columns} />
        </>
      )}
    </div>
  );
}
