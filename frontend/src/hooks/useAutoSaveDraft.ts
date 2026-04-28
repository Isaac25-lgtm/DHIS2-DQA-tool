import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getAssessmentDraft,
  markDraftPendingSync,
  saveAssessmentDraft,
} from "../services/offlineStore";
import type {
  AssessmentDraft,
  DraftSourceDocumentCheckInput,
  DraftValueInput,
  LocalDraftSyncStatus,
  SourceDocumentCheckInput,
} from "../types";

interface UseAutoSaveDraftOptions {
  assessmentFacilityId?: string;
  values: DraftValueInput[];
  sourceDocumentChecks: DraftSourceDocumentCheckInput[];
  generalAssessmentComment: string | null;
  enabled: boolean;
  seedDraft?: AssessmentDraft | null;
}

type AutoSaveState = "IDLE" | "SAVING_LOCALLY" | "DRAFT_SAVED_LOCALLY" | "PENDING_SYNC" | "ERROR_SAVING_LOCALLY";

function generateId() {
  if (typeof window !== "undefined" && "crypto" in window && "randomUUID" in window.crypto) {
    return window.crypto.randomUUID();
  }
  return `draft-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function hasMeaningfulValue(
  values: DraftValueInput[],
  checks: DraftSourceDocumentCheckInput[],
  generalAssessmentComment: string | null,
) {
  return (
    Boolean((generalAssessmentComment ?? "").trim()) ||
    values.some(
      (item) =>
        item.register_value !== null ||
        item.hmis105_value !== null ||
        Boolean((item.assessor_comment ?? "").trim()),
    ) ||
    checks.some(
      (item) =>
        item.available !== null ||
        item.complete !== null ||
        item.legible !== null ||
        item.missing_pages !== null ||
        Boolean((item.comment ?? "").trim()),
    )
  );
}

export function toDraftValueInputs(
  values: { indicator_id: string; register_value: number | null; hmis105_value: number | null; assessor_comment: string | null }[],
  existingDraft?: AssessmentDraft | null,
): DraftValueInput[] {
  const existingMap = new Map(existingDraft?.values.map((item) => [item.indicator_id, item]) ?? []);
  const timestamp = new Date().toISOString();
  return values.map((item) => ({
    indicator_id: item.indicator_id,
    register_value: item.register_value,
    hmis105_value: item.hmis105_value,
    assessor_comment: item.assessor_comment,
    local_client_id: existingMap.get(item.indicator_id)?.local_client_id ?? generateId(),
    updated_at_client: timestamp,
  }));
}

export function toDraftSourceDocumentChecks(
  checks: SourceDocumentCheckInput[],
  existingDraft?: AssessmentDraft | null,
): DraftSourceDocumentCheckInput[] {
  const existingMap = new Map(existingDraft?.source_document_checks.map((item) => [item.source_document_name, item]) ?? []);
  const timestamp = new Date().toISOString();
  return checks.map((item) => ({
    ...item,
    updated_at_client: existingMap.get(item.source_document_name)?.updated_at_client ?? timestamp,
  }));
}

export function useAutoSaveDraft({
  assessmentFacilityId,
  values,
  sourceDocumentChecks,
  generalAssessmentComment,
  enabled,
  seedDraft,
}: UseAutoSaveDraftOptions) {
  const [draftState, setDraftState] = useState<AssessmentDraft | null>(seedDraft ?? null);
  const [status, setStatus] = useState<AutoSaveState>(seedDraft ? "PENDING_SYNC" : "IDLE");
  const [statusMessage, setStatusMessage] = useState<string | null>(
    seedDraft ? "Draft restored from this device." : null,
  );
  const skipNextSaveRef = useRef(true);

  useEffect(() => {
    setDraftState(seedDraft ?? null);
  }, [seedDraft]);

  const hasContent = useMemo(
    () => hasMeaningfulValue(values, sourceDocumentChecks, generalAssessmentComment),
    [generalAssessmentComment, values, sourceDocumentChecks],
  );

  const persistDraft = useCallback(
    async (submitFinal = false, forceStatus: LocalDraftSyncStatus = "PENDING_SYNC") => {
      if (!assessmentFacilityId || !enabled || !hasContent) {
        return null;
      }

      setStatus("SAVING_LOCALLY");
      try {
        const existingDraft = draftState ?? (await getAssessmentDraft(assessmentFacilityId));
        const nextDraft: AssessmentDraft = {
          assessment_facility_id: assessmentFacilityId,
          client_draft_id: existingDraft?.client_draft_id ?? generateId(),
          client_batch_id:
            existingDraft &&
            existingDraft.sync_status !== "SYNCED" &&
            existingDraft.sync_status !== "RELOGIN_REQUIRED"
              ? existingDraft.client_batch_id
              : generateId(),
          values,
          source_document_checks: sourceDocumentChecks,
          general_assessment_comment: generalAssessmentComment?.trim() || null,
          submit_final: submitFinal || existingDraft?.submit_final || false,
          sync_status: forceStatus,
          last_saved_at: new Date().toISOString(),
          last_sync_attempt_at: existingDraft?.last_sync_attempt_at ?? null,
          last_synced_at: existingDraft?.last_synced_at ?? null,
          error_message: null,
        };
        await saveAssessmentDraft(nextDraft);
        await markDraftPendingSync(assessmentFacilityId);
        const refreshedDraft = await getAssessmentDraft(assessmentFacilityId);
        setDraftState(refreshedDraft ?? nextDraft);
        setStatus(submitFinal ? "PENDING_SYNC" : "DRAFT_SAVED_LOCALLY");
        setStatusMessage(
          submitFinal
            ? "Assessment marked for submission. It will submit when synced."
            : "Draft saved locally.",
        );
        return refreshedDraft ?? nextDraft;
      } catch {
        setStatus("ERROR_SAVING_LOCALLY");
        setStatusMessage("Unable to save draft locally on this device.");
        return null;
      }
    },
    [assessmentFacilityId, draftState, enabled, generalAssessmentComment, hasContent, sourceDocumentChecks, values],
  );

  useEffect(() => {
    if (!assessmentFacilityId || !enabled) {
      return;
    }
    if (skipNextSaveRef.current) {
      skipNextSaveRef.current = false;
      return;
    }

    const timer = window.setTimeout(() => {
      void persistDraft(false, "PENDING_SYNC");
    }, 700);

    return () => window.clearTimeout(timer);
  }, [assessmentFacilityId, enabled, persistDraft]);

  return {
    draftState,
    status,
    statusMessage,
    saveNow: persistDraft,
    setStatusMessage,
  };
}
