import { api } from "./api";
import type { SubmissionDashboard, SubmissionDetail } from "../types";

const SUBMISSION_EXPORT_TIMEOUT_MS = 180000;

async function downloadBlob(url: string, fallbackFileName: string) {
  const response = await api.get(url, {
    responseType: "blob",
    timeout: SUBMISSION_EXPORT_TIMEOUT_MS,
  });
  const fileName =
    response.headers["content-disposition"]?.match(/filename="?([^"]+)"?/)?.[1] ??
    fallbackFileName;
  const blobUrl = window.URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export const submissionService = {
  async getDashboard(assessmentRoundId?: string | null, teamLeadUserId?: string | null) {
    const response = await api.get<SubmissionDashboard>("/submissions", {
      params: {
        ...(assessmentRoundId ? { assessment_round_id: assessmentRoundId } : {}),
        ...(teamLeadUserId ? { team_lead_user_id: teamLeadUserId } : {}),
      },
    });
    return response.data;
  },

  async getSubmission(assessmentFacilityId: string) {
    const response = await api.get<SubmissionDetail>(`/submissions/${assessmentFacilityId}`);
    return response.data;
  },

  downloadCumulativeXlsx(assessmentRoundId?: string | null, teamLeadUserId?: string | null, assessmentFacilityId?: string | null) {
    const params = new URLSearchParams();
    if (assessmentRoundId) {
      params.set("assessment_round_id", assessmentRoundId);
    }
    if (teamLeadUserId) {
      params.set("team_lead_user_id", teamLeadUserId);
    }
    if (assessmentFacilityId) {
      params.set("assessment_facility_id", assessmentFacilityId);
    }
    const query = params.toString() ? `?${params.toString()}` : "";
    return downloadBlob(`/submissions/export/xlsx${query}`, "ucmb-submissions.xlsx");
  },

  downloadSubmissionXlsx(assessmentFacilityId: string) {
    return downloadBlob(`/submissions/${assessmentFacilityId}/export/xlsx`, "ucmb-submission.xlsx");
  },
};
