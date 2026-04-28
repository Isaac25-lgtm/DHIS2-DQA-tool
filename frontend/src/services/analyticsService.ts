import { api } from "./api";
import type {
  AnalyticsSummary,
  AssessmentFacilityAnalyticsSummary,
  FacilityAnalyticsItem,
  HeatmapCell,
  IndicatorAnalyticsItem,
  SourceDocumentAnalyticsItem,
} from "../types";

export const analyticsService = {
  async getOverallSummary() {
    const response = await api.get<AnalyticsSummary>("/analytics/summary");
    return response.data;
  },

  async getRoundSummary(roundId: string) {
    const response = await api.get<AnalyticsSummary>(`/analytics/assessment-rounds/${roundId}/summary`);
    return response.data;
  },

  async getRoundFacilities(roundId: string) {
    const response = await api.get<FacilityAnalyticsItem[]>(`/analytics/assessment-rounds/${roundId}/facilities`);
    return response.data;
  },

  async getRoundIndicators(roundId: string) {
    const response = await api.get<IndicatorAnalyticsItem[]>(`/analytics/assessment-rounds/${roundId}/indicators`);
    return response.data;
  },

  async getRoundSourceDocuments(roundId: string) {
    const response = await api.get<SourceDocumentAnalyticsItem[]>(`/analytics/assessment-rounds/${roundId}/source-documents`);
    return response.data;
  },

  async getRoundHeatmap(roundId: string) {
    const response = await api.get<HeatmapCell[]>(`/analytics/assessment-rounds/${roundId}/heatmap`);
    return response.data;
  },

  async getAssessmentFacilitySummary(assessmentFacilityId: string) {
    const response = await api.get<AssessmentFacilityAnalyticsSummary>(`/analytics/assessment-facilities/${assessmentFacilityId}/summary`);
    return response.data;
  },
};
