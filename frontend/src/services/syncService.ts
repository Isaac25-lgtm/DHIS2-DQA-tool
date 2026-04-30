import axios from "axios";
import { getAccessToken, hasValidAccessToken } from "../lib/auth";
import { api } from "./api";
import {
  clearSyncedDraft,
  getAssessmentDraft,
  listPendingSyncItems,
  markDraftSyncFailed,
  markDraftSynced,
  markDraftSyncing,
  saveCachedAssessment,
} from "./offlineStore";
import { assessmentWorkspaceService } from "./assessmentWorkspaceService";
import type { AssessmentDraft, SyncAssessmentDraftPayload, SyncDraftResult } from "../types";

function toPayload(draft: AssessmentDraft): SyncAssessmentDraftPayload {
  return {
    assessment_facility_id: draft.assessment_facility_id,
    client_batch_id: draft.client_batch_id,
    client_saved_at: draft.last_saved_at,
    values: draft.values,
    source_document_checks: draft.source_document_checks,
    general_assessment_comment: draft.general_assessment_comment,
    submit_final: draft.submit_final,
  };
}

function buildResult(
  status: SyncDraftResult["status"],
  message: string,
  syncedCount = 0,
  failedCount = 0,
  response?: SyncDraftResult["response"],
): SyncDraftResult {
  return { status, message, syncedCount, failedCount, response };
}

async function refreshCachedWorkspace(assessmentFacilityId: string) {
  try {
    const workspace = await assessmentWorkspaceService.getWorkspace(assessmentFacilityId);
    await saveCachedAssessment(workspace);
  } catch {
    // Keep the local draft even if the cache refresh fails.
  }
}

export const syncService = {
  async syncAssessmentDraft(assessmentFacilityId: string): Promise<SyncDraftResult> {
    const draft = await getAssessmentDraft(assessmentFacilityId);
    if (!draft) {
      return buildResult("NO_PENDING_DRAFTS", "No local draft is available for sync.");
    }

    if (!getAccessToken() || !hasValidAccessToken()) {
      await markDraftSyncFailed(assessmentFacilityId, "Please log in again to sync your saved draft.", true);
      return buildResult("RELOGIN_REQUIRED", "Please log in again to sync your saved draft.");
    }

    await markDraftSyncing(assessmentFacilityId);
    const payload = toPayload(draft);

    try {
      const response = await api.post("/sync/assessment-draft", payload);
      const data = response.data;
      await markDraftSynced(assessmentFacilityId, data);
      await refreshCachedWorkspace(assessmentFacilityId);

      if (!draft.submit_final) {
        await clearSyncedDraft(assessmentFacilityId);
      }

      return buildResult(
        "SYNCED",
        data.message ?? "Synced successfully.",
        1,
        0,
        data,
      );
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        await markDraftSyncFailed(assessmentFacilityId, "Please log in again to sync your saved draft.", true);
        return buildResult("RELOGIN_REQUIRED", "Please log in again to sync your saved draft.");
      }

      if (axios.isAxiosError(error) && error.response?.status === 404) {
        const message =
          "The manager deleted this assessment from the server. Your assessor-side draft is still saved on this device so it can be reused if the assessment is recreated.";
        await markDraftSyncFailed(assessmentFacilityId, message);
        return buildResult("FAILED", message, 0, 1);
      }

      const message =
        axios.isAxiosError(error) && typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "Sync failed. Your draft is still saved locally. Try again when the network improves.";
      await markDraftSyncFailed(assessmentFacilityId, message);
      return buildResult("FAILED", message, 0, 1);
    }
  },

  async syncAllPendingDrafts(): Promise<SyncDraftResult> {
    const drafts = await listPendingSyncItems();
    if (drafts.length === 0) {
      return buildResult("NO_PENDING_DRAFTS", "No pending drafts are waiting to sync.");
    }

    if (!getAccessToken() || !hasValidAccessToken()) {
      for (const draft of drafts) {
        await markDraftSyncFailed(draft.assessment_facility_id, "Please log in again to sync your saved drafts.", true);
      }
      return buildResult("RELOGIN_REQUIRED", "Please log in again to sync your saved drafts.");
    }

    let syncedCount = 0;
    let failedCount = 0;
    let lastFailureMessage: string | null = null;

    for (const draft of drafts) {
      const result = await this.syncAssessmentDraft(draft.assessment_facility_id);
      if (result.status === "SYNCED") {
        syncedCount += 1;
      } else if (result.status !== "NO_PENDING_DRAFTS") {
        failedCount += 1;
        lastFailureMessage = result.message;
      }
    }

    if (failedCount > 0) {
      return buildResult(
        "FAILED",
        lastFailureMessage ?? "Some drafts could not be synced.",
        syncedCount,
        failedCount,
      );
    }

    return buildResult("SYNCED", "All pending drafts synced successfully.", syncedCount, 0);
  },
};
