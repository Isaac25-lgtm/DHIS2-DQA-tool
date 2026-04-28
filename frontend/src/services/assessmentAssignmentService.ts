import { api } from "./api";
import type {
  AssessmentAssignmentPayload,
  AssessmentFacilityAssignment,
  AssessmentRoundPackage,
  AssessmentTeamAssignmentPayload,
  AssessmentTeamMember,
  MyAssessmentListItem,
} from "../types";

export const assessmentAssignmentService = {
  async assignAssessors(roundId: string, payload: AssessmentAssignmentPayload) {
    const response = await api.post<AssessmentFacilityAssignment[]>(`/assessment-rounds/${roundId}/assign`, payload);
    return response.data;
  },

  async listMyAssessments() {
    const response = await api.get<MyAssessmentListItem[]>("/my-assessments");
    return response.data;
  },

  async getMyAssessmentPackage(assessmentFacilityId: string) {
    const response = await api.get<AssessmentRoundPackage>(`/my-assessments/${assessmentFacilityId}`);
    return response.data;
  },

  async listTeamMembers(assessmentFacilityId: string) {
    const response = await api.get<AssessmentTeamMember[]>(`/assessment-facilities/${assessmentFacilityId}/team-members`);
    return response.data;
  },

  async saveTeamMembers(assessmentFacilityId: string, payload: AssessmentTeamAssignmentPayload) {
    const response = await api.put<AssessmentTeamMember[]>(
      `/assessment-facilities/${assessmentFacilityId}/team-members`,
      payload,
    );
    return response.data;
  },
};
