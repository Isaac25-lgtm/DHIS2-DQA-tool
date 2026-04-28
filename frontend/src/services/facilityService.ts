import { api } from "./api";
import type { Dhis2FacilitySearchResult, Facility, FacilityFormPayload } from "../types";

export const facilityService = {
  async listFacilities(params?: { search?: string; active?: boolean | "all" }) {
    const queryParams =
      params && params.active !== "all"
        ? { search: params.search, active: params.active }
        : { search: params?.search };
    const { data } = await api.get<Facility[]>("/facilities", { params: queryParams });
    return data;
  },

  async createFacility(payload: FacilityFormPayload) {
    const { data } = await api.post<Facility>("/facilities", payload);
    return data;
  },

  async importFromDhis2(payload: Dhis2FacilitySearchResult & { ownership?: string | null }) {
    const { data } = await api.post<Facility>("/facilities/import-from-dhis2", {
      ...payload,
      ownership: payload.ownership ?? "Other",
    });
    return data;
  },

  async updateFacility(facilityId: string, payload: FacilityFormPayload) {
    const { data } = await api.put<Facility>(`/facilities/${facilityId}`, payload);
    return data;
  },

  async activateFacility(facilityId: string) {
    const { data } = await api.patch<Facility>(`/facilities/${facilityId}/activate`);
    return data;
  },

  async deactivateFacility(facilityId: string) {
    const { data } = await api.patch<Facility>(`/facilities/${facilityId}/deactivate`);
    return data;
  },
};
