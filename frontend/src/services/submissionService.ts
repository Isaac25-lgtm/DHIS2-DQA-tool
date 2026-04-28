import { api } from "./api";
import type { SubmissionDashboard, SubmissionDetail } from "../types";

async function downloadBlob(url: string, fallbackFileName: string) {
  const response = await api.get(url, { responseType: "blob" });
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
  async getDashboard(assessmentRoundId?: string | null) {
    const response = await api.get<SubmissionDashboard>("/submissions", {
      params: assessmentRoundId ? { assessment_round_id: assessmentRoundId } : undefined,
    });
    return response.data;
  },

  async getSubmission(assessmentFacilityId: string) {
    const response = await api.get<SubmissionDetail>(`/submissions/${assessmentFacilityId}`);
    return response.data;
  },

  downloadCumulativeXlsx(assessmentRoundId?: string | null) {
    const query = assessmentRoundId ? `?assessment_round_id=${assessmentRoundId}` : "";
    return downloadBlob(`/submissions/export/xlsx${query}`, "ucmb-submissions.xlsx");
  },

  downloadSubmissionXlsx(assessmentFacilityId: string) {
    return downloadBlob(`/submissions/${assessmentFacilityId}/export/xlsx`, "ucmb-submission.xlsx");
  },
};
