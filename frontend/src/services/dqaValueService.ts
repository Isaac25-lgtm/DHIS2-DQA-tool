import { api } from "./api";
import type { DqaValueInput, SaveValuesResponse, SaveSourceDocumentsResponse, SourceDocumentCheckInput } from "../types";

export const dqaValueService = {
  async saveValues(assessmentFacilityId: string, values: DqaValueInput[]) {
    const response = await api.post<SaveValuesResponse>(`/my-assessments/${assessmentFacilityId}/values`, { values });
    return response.data;
  },

  async saveSourceDocuments(assessmentFacilityId: string, checks: SourceDocumentCheckInput[]) {
    const response = await api.post<SaveSourceDocumentsResponse>(
      `/my-assessments/${assessmentFacilityId}/source-documents`,
      { checks },
    );
    return response.data;
  },

  async saveGeneralComment(assessmentFacilityId: string, generalAssessmentComment: string | null) {
    const response = await api.post<{
      status: string;
      message: string;
      assessment_status: string;
      general_assessment_comment: string | null;
    }>(`/my-assessments/${assessmentFacilityId}/general-comment`, {
      general_assessment_comment: generalAssessmentComment,
    });
    return response.data;
  },
};
