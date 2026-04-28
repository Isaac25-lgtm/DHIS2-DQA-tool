import { api } from "./api";
import type { AssessmentWorkspace, SubmitAssessmentResponse } from "../types";

export const assessmentWorkspaceService = {
  async getWorkspace(assessmentFacilityId: string) {
    const response = await api.get<AssessmentWorkspace>(`/my-assessments/${assessmentFacilityId}/workspace`);
    return response.data;
  },

  async getReviewWorkspace(assessmentFacilityId: string) {
    const response = await api.get<AssessmentWorkspace>(`/assessment-facilities/${assessmentFacilityId}/workspace`);
    return response.data;
  },

  async submitAssessment(assessmentFacilityId: string) {
    const response = await api.post<SubmitAssessmentResponse>(`/my-assessments/${assessmentFacilityId}/submit`);
    return response.data;
  },
};
