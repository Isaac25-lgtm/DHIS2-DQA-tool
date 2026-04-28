import { api } from "./api";
import type {
  AssessmentFacilityAssignment,
  AssessmentFacilitySelectionPayload,
  AssessmentPublishPayload,
  AssessmentRound,
  AssessmentRoundListItem,
  AssessmentRoundPayload,
  AssessmentRoundProgress,
  SelectedIndicator,
  SelectedIndicatorPayload,
} from "../types";

export const assessmentRoundService = {
  async listRounds() {
    const response = await api.get<AssessmentRoundListItem[]>("/assessment-rounds");
    return response.data;
  },

  async createRound(payload: AssessmentRoundPayload) {
    const response = await api.post<AssessmentRound>("/assessment-rounds", payload);
    return response.data;
  },

  async getRound(roundId: string) {
    const response = await api.get<AssessmentRound>(`/assessment-rounds/${roundId}`);
    return response.data;
  },

  async updateRound(roundId: string, payload: AssessmentRoundPayload) {
    const response = await api.put<AssessmentRound>(`/assessment-rounds/${roundId}`, payload);
    return response.data;
  },

  async archiveRound(roundId: string) {
    const response = await api.patch<AssessmentRound>(`/assessment-rounds/${roundId}/archive`);
    return response.data;
  },

  async addIndicators(roundId: string, indicators: SelectedIndicatorPayload[]) {
    const response = await api.post<SelectedIndicator[]>(`/assessment-rounds/${roundId}/indicators`, { indicators });
    return response.data;
  },

  async replaceIndicators(roundId: string, indicators: SelectedIndicatorPayload[]) {
    const response = await api.put<SelectedIndicator[]>(`/assessment-rounds/${roundId}/indicators`, { indicators });
    return response.data;
  },

  async deleteIndicator(roundId: string, indicatorId: string) {
    await api.delete(`/assessment-rounds/${roundId}/indicators/${indicatorId}`);
  },

  async addFacilities(roundId: string, payload: AssessmentFacilitySelectionPayload) {
    const response = await api.post<AssessmentFacilityAssignment[]>(`/assessment-rounds/${roundId}/facilities`, payload);
    return response.data;
  },

  async replaceFacilities(roundId: string, payload: AssessmentFacilitySelectionPayload) {
    const response = await api.put<AssessmentFacilityAssignment[]>(`/assessment-rounds/${roundId}/facilities`, payload);
    return response.data;
  },

  async publishRound(roundId: string, payload: AssessmentPublishPayload) {
    const response = await api.post<AssessmentRound>(`/assessment-rounds/${roundId}/publish`, payload);
    return response.data;
  },

  async closeRound(roundId: string) {
    const response = await api.post<AssessmentRound>(`/assessment-rounds/${roundId}/close`);
    return response.data;
  },

  async getProgress(roundId: string) {
    const response = await api.get<AssessmentRoundProgress>(`/assessment-rounds/${roundId}/progress`);
    return response.data;
  },
};
