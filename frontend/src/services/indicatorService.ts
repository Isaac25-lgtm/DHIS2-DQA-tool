import { api } from "./api";
import type { Dhis2DataElementSearchResult, Indicator, IndicatorFilters, IndicatorFormPayload, IndicatorSeedResponse } from "../types";

export const indicatorService = {
  async listIndicators(filters?: IndicatorFilters) {
    const { data } = await api.get<Indicator[]>("/indicators", { params: filters });
    return data;
  },

  async createIndicator(payload: IndicatorFormPayload) {
    const { data } = await api.post<Indicator>("/indicators", payload);
    return data;
  },

  async importFromDhis2(
    payload: Dhis2DataElementSearchResult & {
      indicator_group?: string;
      hmis_section?: string | null;
      source_register?: string | null;
      default_discrepancy_threshold_percent?: number;
      is_death_indicator?: boolean;
      sort_order?: number;
      notes?: string | null;
    },
  ) {
    const { data } = await api.post<Indicator>("/indicators/import-from-dhis2", {
      indicator_name: payload.name,
      hmis_code: payload.hmis_code ?? payload.data_element_uid,
      dhis2_uid_or_operand: payload.dhis2_uid_or_operand,
      data_element_uid: payload.data_element_uid,
      category_option_combo_uid: null,
      dataset_name: payload.dataset_name ?? null,
      hmis_section: payload.hmis_section ?? null,
      source_register: payload.source_register ?? null,
      category_combo: payload.category_combo ?? null,
      value_type: payload.value_type ?? "INTEGER_ZERO_OR_POSITIVE",
      aggregation_type: payload.aggregation_type ?? null,
      indicator_group: payload.indicator_group ?? "Other",
      is_active: true,
      is_required_by_default: true,
      default_discrepancy_threshold_percent: payload.default_discrepancy_threshold_percent ?? 5,
      is_death_indicator: payload.is_death_indicator ?? false,
      sort_order: payload.sort_order ?? 0,
      notes: payload.notes ?? null,
    });
    return data;
  },

  async updateIndicator(indicatorId: string, payload: IndicatorFormPayload) {
    const { data } = await api.put<Indicator>(`/indicators/${indicatorId}`, payload);
    return data;
  },

  async activateIndicator(indicatorId: string) {
    const { data } = await api.patch<Indicator>(`/indicators/${indicatorId}/activate`);
    return data;
  },

  async deactivateIndicator(indicatorId: string) {
    const { data } = await api.patch<Indicator>(`/indicators/${indicatorId}/deactivate`);
    return data;
  },

  async seedConfirmedIndicators() {
    const { data } = await api.post<IndicatorSeedResponse>("/indicators/seed-confirmed");
    return data;
  },
};
