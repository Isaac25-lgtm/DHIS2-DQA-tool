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
            <p className="text-brand-muted">{row.original.period_type}</p>
            <p className="text-xs text-brand-muted">
              {row.original.start_date && row.original.end_date
                ? `${row.original.start_date} to ${row.original.end_date}`
                : "Date window not set"}
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
        <Table data={rounds} columns={columns} />
      )}
    </div>
  );
}
