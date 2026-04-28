import { api } from "./api";
import type {
  CorrectiveAction,
  CorrectiveActionPayload,
  CorrectiveActionStatus,
  CorrectiveActionSuggestionResponse,
} from "../types";

export const correctiveActionService = {
  async listActions() {
    const response = await api.get<CorrectiveAction[]>("/corrective-actions");
    return response.data;
  },

  async createAction(payload: CorrectiveActionPayload) {
    const response = await api.post<CorrectiveAction>("/corrective-actions", payload);
    return response.data;
  },

  async getAction(actionId: string) {
    const response = await api.get<CorrectiveAction>(`/corrective-actions/${actionId}`);
    return response.data;
  },

  async updateAction(actionId: string, payload: CorrectiveActionPayload & { status?: CorrectiveActionStatus | null; resolution_comment?: string | null; verification_comment?: string | null }) {
    const response = await api.put<CorrectiveAction>(`/corrective-actions/${actionId}`, payload);
    return response.data;
  },

  async updateStatus(actionId: string, status: CorrectiveActionStatus, manager_comment?: string | null) {
    const response = await api.patch<CorrectiveAction>(`/corrective-actions/${actionId}/status`, { status, manager_comment: manager_comment ?? null });
    return response.data;
  },

  async resolve(actionId: string, resolution_comment?: string | null) {
    const response = await api.post<CorrectiveAction>(`/corrective-actions/${actionId}/resolve`, { resolution_comment: resolution_comment ?? null });
    return response.data;
  },

  async verify(actionId: string, verification_comment?: string | null) {
    const response = await api.post<CorrectiveAction>(`/corrective-actions/${actionId}/verify`, { verification_comment: verification_comment ?? null });
    return response.data;
  },

  async close(actionId: string, manager_comment?: string | null) {
    const response = await api.post<CorrectiveAction>(`/corrective-actions/${actionId}/close`, { manager_comment: manager_comment ?? null });
    return response.data;
  },

  async suggestForAssessment(assessmentFacilityId: string) {
    const response = await api.post<CorrectiveActionSuggestionResponse>(`/assessment-facilities/${assessmentFacilityId}/suggest-corrective-actions`);
    return response.data;
  },

  async suggestForRound(roundId: string) {
    const response = await api.post<CorrectiveActionSuggestionResponse>(`/assessment-rounds/${roundId}/suggest-corrective-actions`);
    return response.data;
  },
};
