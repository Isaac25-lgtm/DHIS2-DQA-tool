import { api } from "./api";
import type { Dhis2ConnectionStatus, Dhis2DataElementSearchResult, Dhis2FacilitySearchResult, Dhis2LoginPayload, Dhis2Value } from "../types";

interface Dhis2PullResponse {
  values: Dhis2Value[];
  message: string | null;
}

export const dhis2Service = {
  async getConnectionStatus() {
    const response = await api.get<Dhis2ConnectionStatus>("/dhis2/connection-status");
    return response.data;
  },

  async login(payload: Dhis2LoginPayload) {
    const response = await api.post<Dhis2ConnectionStatus>("/dhis2/session/login", payload);
    return response.data;
  },

  async logout() {
    const response = await api.post<Dhis2ConnectionStatus>("/dhis2/session/logout");
    return response.data;
  },

  async searchFacilities(query: string) {
    const response = await api.get<Dhis2FacilitySearchResult[]>("/dhis2/facilities/search", {
      params: { query },
    });
    return response.data;
  },

  async searchDataElements(query: string) {
    const response = await api.get<Dhis2DataElementSearchResult[]>("/dhis2/data-elements/search", {
      params: { query },
    });
    return response.data;
  },

  async retryAssessmentPull(assessmentFacilityId: string) {
    const response = await api.post<Dhis2PullResponse>(`/my-assessments/${assessmentFacilityId}/pull-dhis2`);
    return response.data;
  },

  async syncAssessmentWithDhis2(assessmentFacilityId: string) {
    const response = await api.post<Dhis2PullResponse>(`/my-assessments/${assessmentFacilityId}/sync-with-dhis2`);
    return response.data;
  },

  async refreshLatestValues(assessmentFacilityId: string) {
    const response = await api.post<Dhis2PullResponse>(`/assessment-facilities/${assessmentFacilityId}/refresh-dhis2-values`);
    return response.data;
  },

  async syncRoundValues(roundId: string) {
    const response = await api.post<{ status: string; synced_facilities: number; failed_facilities: number }>(
      `/assessment-rounds/${roundId}/sync-dhis2-values`,
    );
    return response.data;
  },
};
