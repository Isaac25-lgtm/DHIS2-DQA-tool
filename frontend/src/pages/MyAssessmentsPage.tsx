import { useCallback, useEffect, useMemo, useState } from "react";
import { Cloud, MapPinned } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { assessmentAssignmentService } from "../services/assessmentAssignmentService";
import {
  getAssessmentDraft,
  listCachedAssessments,
} from "../services/offlineStore";
import { useNetworkStatus } from "../hooks/useNetworkStatus";
import type {
  AssessmentDraft,
  CachedAssessmentWorkspace,
  MyAssessmentListItem,
} from "../types";

const statusTone: Record<string, "neutral" | "success" | "warning" | "danger" | "info"> = {
  NOT_STARTED: "neutral",
  ASSIGNED: "info",
  IN_PROGRESS: "warning",
  DRAFT_SAVED: "warning",
  PENDING_SYNC: "warning",
  SUBMITTED: "success",
  UNDER_REVIEW: "info",
  RETURNED_FOR_CORRECTION: "danger",
  APPROVED: "success",
  CLOSED: "neutral",
};

interface CachedAssessmentCardItem {
  id: string;
  round_name: string;
  facility_name: string;
  district: string;
  reporting_period: string;
  deadline: string | null;
  status: string;
  cached: true;
  my_team_role?: string | null;
  can_submit?: boolean;
}

export function MyAssessmentsPage() {
  const { isOnline } = useNetworkStatus();
  const [items, setItems] = useState<MyAssessmentListItem[]>([]);
  const [cachedItems, setCachedItems] = useState<CachedAssessmentCardItem[]>([]);
  const [draftsByAssessmentId, setDraftsByAssessmentId] = useState<Record<string, AssessmentDraft | null>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAssessments = useCallback(
    async (showLoading = true) => {
      if (showLoading) {
        setLoading(true);
      }
      setError(null);
      try {
        if (isOnline) {
          const data = await assessmentAssignmentService.listMyAssessments();
          setItems(data);
          const drafts = await Promise.all(data.map((item) => getAssessmentDraft(item.id)));
          setDraftsByAssessmentId(
            data.reduce<Record<string, AssessmentDraft | null>>((accumulator, item, index) => {
              accumulator[item.id] = drafts[index];
              return accumulator;
            }, {}),
          );
          setCachedItems([]);
        } else {
          const cached = await listCachedAssessments();
          const offlineItems = cached.map((item) => ({
            id: item.assessment_facility_id,
            round_name: item.workspace.assessment_round.name,
            facility_name: item.workspace.facility.facility_name,
            district: item.workspace.facility.district,
            reporting_period: item.workspace.assessment_round.reporting_period,
            deadline: item.workspace.assessment_round.deadline,
            status: item.assessment_status,
            cached: true as const,
            my_team_role: null,
            can_submit: false,
          }));
          setCachedItems(offlineItems);
          const drafts = await Promise.all(cached.map((item) => getAssessmentDraft(item.assessment_facility_id)));
          setDraftsByAssessmentId(
            cached.reduce<Record<string, AssessmentDraft | null>>((accumulator, item, index) => {
              accumulator[item.assessment_facility_id] = drafts[index];
              return accumulator;
            }, {}),
          );
          setItems([]);
        }
      } catch {
        setError("Unable to load your assigned assessments right now.");
      } finally {
        if (showLoading) {
          setLoading(false);
        }
      }
    },
    [isOnline],
  );

  useEffect(() => {
    void loadAssessments(true);
  }, [loadAssessments]);

  useEffect(() => {
    if (!isOnline) {
      return;
    }
    const intervalId = window.setInterval(() => {
      void loadAssessments(false);
    }, 30000);
    return () => window.clearInterval(intervalId);
  }, [isOnline, loadAssessments]);

  const visibleItems = useMemo(() => {
    return isOnline ? items : cachedItems;
  }, [cachedItems, isOnline, items]);

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-[1.4fr_0.6fr]">
        <div className="rounded-2xl border border-brand-border/70 bg-brand-navy px-6 py-5 text-white shadow-soft">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200">Assessor Workspace</p>
          <h1 className="mt-2 text-2xl font-bold">My Assessments</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-200">
            Open only the facilities assigned to you, continue working offline after first load, and sync drafts when
            network returns.
          </p>
        </div>
        <Card>
          <div className="flex items-center gap-3">
            <Cloud className="text-brand-teal" size={18} />
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-brand-muted">Connectivity</p>
              <p className="mt-1 text-lg font-semibold text-brand-text">{isOnline ? "Online" : "Offline"}</p>
              <p className="mt-1 text-sm text-brand-muted">
                {isOnline
                  ? "Previously opened assessments are cached for offline field use."
                  : "Only assessments already opened on this device remain available offline."}
              </p>
            </div>
          </div>
        </Card>
      </section>

      <div className="flex flex-wrap gap-3">
        <Badge tone={isOnline ? "success" : "warning"}>
          {isOnline ? "Online save and sync available" : "Offline mode active"}
        </Badge>
        <Badge tone="info">Assigned facilities only</Badge>
      </div>

      {error ? <p className="text-sm text-brand-danger">{error}</p> : null}

      {loading ? (
        <Card>
          <div className="rounded-xl bg-brand-surface px-5 py-6 text-sm text-brand-muted">
            Loading assigned assessments...
          </div>
        </Card>
      ) : visibleItems.length === 0 ? (
        <Card
          title={isOnline ? "No assigned assessments" : "No cached assessments"}
          subtitle={
            isOnline
              ? "Published assignments will appear here once a manager assigns you."
              : "Open an assessment while online once before it can be used offline."
          }
        >
          <p className="text-sm text-brand-muted">
            {isOnline ? "Nothing has been assigned yet." : "This device does not have any previously cached assessments."}
          </p>
        </Card>
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          {visibleItems.map((item) => {
            const draft = draftsByAssessmentId[item.id];
            return (
              <Card key={item.id} className="space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-bold text-brand-navy">{item.round_name}</p>
                    <p className="mt-1 text-sm text-brand-muted">{item.reporting_period}</p>
                  </div>
                  <Badge tone={statusTone[item.status] ?? "neutral"}>{item.status.replace(/_/g, " ")}</Badge>
                </div>

                <div className="rounded-xl bg-brand-surface px-4 py-4">
                  <div className="flex items-center gap-2 text-brand-muted">
                    <MapPinned size={16} />
                    Facility
                  </div>
                  <p className="mt-2 font-semibold text-brand-text">{item.facility_name}</p>
                  <p className="mt-1 text-sm text-brand-muted">{item.district}</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {"cached" in item ? <Badge tone="info">Cached</Badge> : null}
                  {draft ? (
                    <Badge tone={draft.sync_status === "SYNC_FAILED" || draft.sync_status === "RELOGIN_REQUIRED" ? "warning" : "info"}>
                      {draft.sync_status.replace(/_/g, " ")}
                    </Badge>
                  ) : null}
                  {item.my_team_role ? (
                    <Badge tone={item.my_team_role === "TEAM_LEAD" || item.my_team_role === "LEGACY_LEAD" ? "success" : "info"}>
                      Shared group access
                    </Badge>
                  ) : null}
                  {item.can_submit ? <Badge tone="success">Can submit</Badge> : null}
                </div>

                <div className="text-sm text-brand-muted">Deadline: {item.deadline ?? "No deadline set"}</div>

                <Link to={`/my-assessments/${item.id}`}>
                  <Button>{isOnline ? "Open assessment workspace" : "Open cached assessment"}</Button>
                </Link>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
