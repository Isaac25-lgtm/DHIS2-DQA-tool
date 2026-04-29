import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCcw, Save, Send } from "lucide-react";
import { useLocation, useParams } from "react-router-dom";
import { AssessmentSummaryCard } from "../components/assessment/AssessmentSummaryCard";
import { AssessmentValueTable } from "../components/assessment/AssessmentValueTable";
import { SyncBanner } from "../components/sync/SyncBanner";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Textarea } from "../components/ui/Textarea";
import { useAutoSaveDraft, toDraftValueInputs } from "../hooks/useAutoSaveDraft";
import { useAuth } from "../hooks/useAuth";
import { useNetworkStatus } from "../hooks/useNetworkStatus";
import { assessmentAssignmentService } from "../services/assessmentAssignmentService";
import { assessmentWorkspaceService } from "../services/assessmentWorkspaceService";
import { dhis2Service } from "../services/dhis2Service";
import {
  getAssessmentDraft,
  getCachedAssessment,
  saveCachedAssessment,
} from "../services/offlineStore";
import { syncService } from "../services/syncService";
import type {
  AssessmentDraft,
  AssessmentWorkspace,
  DqaValue,
  SyncDraftResult,
} from "../types";

function buildEditableValues(workspace: AssessmentWorkspace): DqaValue[] {
  const valuesByIndicator = new Map(workspace.values.map((item) => [item.indicator_id, item]));
  return workspace.selected_indicators.map((indicator) => {
    const existing = valuesByIndicator.get(indicator.indicator_id);
    return (
      existing ?? {
        id: indicator.id,
        indicator_id: indicator.indicator_id,
        register_value: null,
        hmis105_value: null,
        dhis2_value_at_assessment: null,
        dhis2_extracted_at: null,
        dhis2_api_status: null,
        dhis2_error_message: null,
        dhis2_value_latest: null,
        dhis2_latest_extracted_at: null,
        dhis2_latest_api_status: null,
        dhis2_latest_error_message: null,
        assessor_comment: null,
        manager_comment: null,
        register_vs_hmis_difference: null,
        hmis_vs_dhis2_difference: null,
        register_vs_dhis2_difference: null,
        absolute_discrepancy: null,
        discrepancy_percent: null,
        verification_factor: null,
        issue_type: null,
        severity: null,
        comparison_status: null,
        comparison_notes: null,
        compared_at: null,
        compared_by_user_id: null,
        value_status: "NOT_STARTED",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
    );
  });
}

function mergeDraftIntoValues(serverValues: DqaValue[], draft: AssessmentDraft | null): DqaValue[] {
  if (!draft) {
    return serverValues;
  }
  const draftMap = new Map(draft.values.map((item) => [item.indicator_id, item]));
  return serverValues.map((item) => {
    const local = draftMap.get(item.indicator_id);
    if (!local) {
      return item;
    }
    return {
      ...item,
      register_value: local.register_value,
      hmis105_value: local.hmis105_value,
      assessor_comment: local.assessor_comment,
    };
  });
}

function getBannerVariant(result: SyncDraftResult | null, message: string | null) {
  if (result?.status === "RELOGIN_REQUIRED") {
    return "relogin" as const;
  }
  if (result?.status === "FAILED") {
    return "failed" as const;
  }
  if (result?.status === "SYNCED") {
    return "synced" as const;
  }
  if (message?.includes("offline")) {
    return "offline" as const;
  }
  return "info" as const;
}

export function AssessmentWorkspacePage() {
  const { assessmentFacilityId } = useParams();
  const location = useLocation();
  const { user } = useAuth();
  const { isOnline, wasOffline } = useNetworkStatus();
  const [workspace, setWorkspace] = useState<AssessmentWorkspace | null>(null);
  const [editableValues, setEditableValues] = useState<DqaValue[]>([]);
  const [generalAssessmentComment, setGeneralAssessmentComment] = useState("");
  const [seedDraft, setSeedDraft] = useState<AssessmentDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncingWithDhis2, setSyncingWithDhis2] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<SyncDraftResult | null>(null);
  const [hasConflict, setHasConflict] = useState(false);

  const isReviewRoute = location.pathname.startsWith("/assessment-facilities/");

  const loadWorkspace = useCallback(async (options?: { source?: "initial" | "manual" | "automatic" }) => {
    if (!assessmentFacilityId) {
      setError("Assessment workspace id is missing.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const localDraft = !isReviewRoute ? await getAssessmentDraft(assessmentFacilityId) : null;

      if (!isOnline && !isReviewRoute) {
        const cached = await getCachedAssessment(assessmentFacilityId);
        if (!cached) {
          setError("This assessment is not available offline. Please connect to the internet and open it once first.");
          setWorkspace(null);
          setEditableValues([]);
          setSeedDraft(localDraft);
          setLoading(false);
          return;
        }

        const cachedWorkspace = cached.workspace;
        const mergedValues = mergeDraftIntoValues(buildEditableValues(cachedWorkspace), localDraft);
        setWorkspace(cachedWorkspace);
        setEditableValues(mergedValues);
        setGeneralAssessmentComment(localDraft?.general_assessment_comment ?? cachedWorkspace.assessment_facility.general_assessment_comment ?? "");
        setSeedDraft(localDraft);
        setHasConflict(false);
        setMessage("You are offline. Showing cached assessment package.");
        setLoading(false);
        return;
      }

      const nextWorkspace = isReviewRoute
        ? await assessmentWorkspaceService.getReviewWorkspace(assessmentFacilityId)
        : await assessmentWorkspaceService.getWorkspace(assessmentFacilityId);

      setWorkspace(nextWorkspace);
      const mergedValues = mergeDraftIntoValues(buildEditableValues(nextWorkspace), localDraft);
        setEditableValues(mergedValues);
        setGeneralAssessmentComment(localDraft?.general_assessment_comment ?? nextWorkspace.assessment_facility.general_assessment_comment ?? "");
        setSeedDraft(localDraft);
        setHasConflict(Boolean(localDraft && localDraft.sync_status !== "SYNCED"));
        setMessage(
          nextWorkspace.dhis2_pull_message ??
            (options?.source === "automatic" ? "Manager updates were applied automatically." : null),
        );
      if (!isReviewRoute) {
        await saveCachedAssessment(nextWorkspace).catch(() => undefined);
      }
    } catch {
      setError("Unable to load the assessment workspace right now.");
    } finally {
      setLoading(false);
    }
  }, [assessmentFacilityId, isOnline, isReviewRoute]);

  useEffect(() => {
    void loadWorkspace({ source: "initial" });
  }, [loadWorkspace]);

  useEffect(() => {
    if (!assessmentFacilityId || !isOnline || isReviewRoute || !workspace) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void assessmentAssignmentService
        .getMyAssessmentPackage(assessmentFacilityId)
        .then((assessmentPackage) => {
          if (assessmentPackage.offline_cache_version !== workspace.offline_cache_version) {
            void loadWorkspace({ source: "automatic" });
          }
        })
        .catch(() => {
          void loadWorkspace({ source: "automatic" });
        });
    }, 30000);

    return () => window.clearInterval(intervalId);
  }, [assessmentFacilityId, isOnline, isReviewRoute, loadWorkspace, workspace]);

  const draftValues = useMemo(
    () =>
      toDraftValueInputs(
        editableValues.map((item) => ({
          indicator_id: item.indicator_id,
          register_value: item.register_value,
          hmis105_value: item.hmis105_value,
          assessor_comment: item.assessor_comment,
        })),
        seedDraft,
      ),
    [editableValues, seedDraft],
  );

  const { draftState, status: autoSaveStatus, statusMessage, saveNow } = useAutoSaveDraft({
    assessmentFacilityId,
    values: draftValues,
    sourceDocumentChecks: [],
    generalAssessmentComment: generalAssessmentComment || null,
    enabled: Boolean(workspace && workspace.workspace_mode === "EDIT" && !isReviewRoute),
    seedDraft,
  });

  const readOnly = workspace?.workspace_mode === "READ_ONLY";
  const canSyncWithDhis2 =
    Boolean(workspace) &&
    isOnline &&
    ((user?.role === "ASSESSOR" && workspace?.workspace_mode === "EDIT") ||
      (user?.role === "MANAGER" &&
        !["CLOSED", "ARCHIVED"].includes(workspace?.assessment_round.status ?? "")));
  const currentTeamMember = workspace?.assessment_facility.team_members.find((member) => member.user_id === user?.id && member.is_active);
  const canSubmit = Boolean(
    workspace?.workspace_mode === "EDIT" &&
      (workspace.assessment_facility.assigned_assessor_id === user?.id || currentTeamMember?.can_submit),
  );

  const missingRequiredCount = useMemo(() => {
    if (!workspace) {
      return 0;
    }
    return workspace.selected_indicators.filter((indicator) => {
      if (!indicator.is_required) {
        return false;
      }
      const currentValue = editableValues.find((item) => item.indicator_id === indicator.indicator_id);
      const hasRegister = currentValue?.register_value !== null && currentValue?.register_value !== undefined;
      const hasHmis = currentValue?.hmis105_value !== null && currentValue?.hmis105_value !== undefined;
      const hasComment = Boolean((currentValue?.assessor_comment ?? "").trim());
      return !(hasRegister && hasHmis) && !hasComment;
    }).length;
  }, [editableValues, workspace]);

  const updateValue = (indicatorId: string, updates: Partial<DqaValue>) => {
    setEditableValues((current) =>
      current.map((item) =>
        item.indicator_id === indicatorId
          ? {
              ...item,
              ...updates,
            }
          : item,
      ),
    );
  };

  const handleSyncWithDhis2 = async () => {
    if (!assessmentFacilityId) {
      return;
    }

    if (!isOnline) {
      setMessage("You are offline. Your work is saved locally and will sync when network returns.");
      return;
    }

    setSyncingWithDhis2(true);
    setMessage(null);
    try {
      const savedDraft = await saveNow(false, "PENDING_SYNC");
      if (savedDraft) {
        const draftSync = await syncService.syncAssessmentDraft(assessmentFacilityId);
        setSyncResult(draftSync);
        if (draftSync.status === "FAILED" || draftSync.status === "RELOGIN_REQUIRED") {
          setMessage(draftSync.message);
          return;
        }
      }
      const response = await dhis2Service.syncAssessmentWithDhis2(assessmentFacilityId);
      await loadWorkspace({ source: "manual" });
      setMessage(response.message ?? "Synced with DHIS2.");
    } catch (retryError) {
      setMessage(retryError instanceof Error ? retryError.message : "Sync with DHIS2 failed.");
    } finally {
      setSyncingWithDhis2(false);
    }
  };

  const handleSubmitAssessment = async () => {
    if (!assessmentFacilityId) {
      return;
    }

    setSubmitting(true);
    setSyncResult(null);
    try {
      if (!isOnline) {
        await saveNow(true, "PENDING_SYNC");
        setMessage("Assessment marked to send to manager. It will submit when synced.");
        return;
      }

      await saveNow(true, "PENDING_SYNC");
      const result = await syncService.syncAssessmentDraft(assessmentFacilityId);
      setSyncResult(result);
      setMessage(result.message);
      if (result.status === "SYNCED") {
        await loadWorkspace({ source: "manual" });
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Card title="Assessment Workspace" subtitle="Preparing the field assessment workspace.">
        <div className="rounded-xl bg-brand-surface px-5 py-6 text-sm text-brand-muted">
          Loading assessment workspace...
        </div>
      </Card>
    );
  }

  if (error || !workspace) {
    return (
      <Card title="Assessment Workspace Unavailable" subtitle="The assessment package could not be loaded.">
        <p className="text-sm text-brand-danger">{error ?? "No assessment workspace data is available."}</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <AssessmentSummaryCard workspace={workspace} missingRequiredCount={missingRequiredCount} />

      {!isOnline ? (
        <SyncBanner
          variant="offline"
          message="You are offline. Your work is being saved on this device."
        />
      ) : wasOffline ? (
        <SyncBanner variant="synced" message="You are back online." />
      ) : null}
      {readOnly ? (
        <SyncBanner
          variant="info"
          message="This workspace is in read-only mode. Submitted, closed, and review views cannot be edited."
        />
      ) : null}
      {hasConflict ? (
        <SyncBanner
          variant="pending"
          message="This assessment has server updates and local unsynced changes. Local draft fields remain on screen until you sync or reload."
        />
      ) : null}
      {draftState?.sync_status === "RELOGIN_REQUIRED" ? (
        <SyncBanner variant="relogin" message="Please log in again to sync your saved draft." />
      ) : null}
      {draftState?.sync_status === "SYNC_FAILED" ? (
        <SyncBanner
          variant="failed"
          message={draftState.error_message ?? "Sync failed. Your draft is still saved locally. Try again when the network improves."}
        />
      ) : null}
      {draftState?.sync_status === "PENDING_SYNC" || draftState?.sync_status === "DRAFT_SAVED_LOCALLY" ? (
        <SyncBanner variant="pending" message="Your draft is saved locally and pending sync." />
      ) : null}
      {syncingWithDhis2 ? <SyncBanner variant="syncing" message="Syncing with DHIS2..." /> : null}
      {syncResult || message || statusMessage ? (
        <SyncBanner
          variant={getBannerVariant(syncResult, message ?? statusMessage ?? null)}
          message={syncResult?.message ?? message ?? statusMessage ?? ""}
        />
      ) : null}

      <section className="sticky bottom-4 z-10 rounded-[22px] border border-brand-border bg-white/95 px-5 py-4 shadow-panel backdrop-blur">
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="secondary"
            className="gap-2"
            onClick={() => void saveNow(false, "PENDING_SYNC")}
            disabled={Boolean(readOnly)}
          >
            <Save size={16} />
            Save locally
          </Button>
          <Button
            variant="secondary"
            className="gap-2"
            onClick={() => void handleSyncWithDhis2()}
            disabled={!canSyncWithDhis2 || syncingWithDhis2}
          >
            <RefreshCcw size={16} />
            {!isOnline ? "Offline - saved locally" : syncingWithDhis2 ? "Syncing..." : "Sync with DHIS2"}
          </Button>
          {canSubmit ? (
            <Button className="ml-auto gap-2" onClick={() => void handleSubmitAssessment()} disabled={submitting}>
              <Send size={16} />
              {submitting ? "Sending..." : isOnline ? "Send to Manager" : "Mark to send"}
            </Button>
          ) : workspace.workspace_mode === "EDIT" ? (
            <Button className="ml-auto" disabled>Only the assigned shared group login can send this assessment</Button>
          ) : null}
        </div>
      </section>

      {workspace.dhis2_pull_message ? (
        <SyncBanner
          variant="pending"
          message="DHIS2 values are not available yet. You can continue entering register and HMIS 105 values."
        />
      ) : null}

      <Card
        title="Assessment values"
        subtitle="Compare register recount, HMIS 105 report, and read-only DHIS2 system values."
      >
        <AssessmentValueTable
          indicators={workspace.selected_indicators}
          values={editableValues}
          onChange={updateValue}
          disabled={Boolean(readOnly)}
        />
      </Card>

      <Card title="General facility assessment comment" subtitle="Summarize document or reporting issues for this facility.">
        <Textarea
          rows={4}
          value={generalAssessmentComment}
          onChange={(event) => setGeneralAssessmentComment(event.target.value)}
          disabled={Boolean(readOnly)}
          placeholder="Example: Maternity register incomplete; HMIS 105 report verified with records officer."
        />
      </Card>

      {autoSaveStatus === "ERROR_SAVING_LOCALLY" ? (
        <SyncBanner variant="failed" message="Unable to save draft locally on this device." />
      ) : null}
    </div>
  );
}
