import { api } from "./api";
import type {
  AssessmentComparisonResults,
  AssessmentRoundComparisonSummary,
  ComparisonRunResponse,
} from "../types";

export const comparisonService = {
  async runAssessmentFacilityComparison(assessmentFacilityId: string) {
    const response = await api.post<ComparisonRunResponse>(`/assessment-facilities/${assessmentFacilityId}/run-comparison`);
    return response.data;
  },

  async getAssessmentFacilityComparisonResults(assessmentFacilityId: string) {
    const response = await api.get<AssessmentComparisonResults>(`/assessment-facilities/${assessmentFacilityId}/comparison-results`);
    return response.data;
  },

  async runAssessmentRoundComparison(roundId: string) {
    const response = await api.post<AssessmentRoundComparisonSummary>(`/assessment-rounds/${roundId}/run-comparison`);
    return response.data;
  },

  async getAssessmentRoundComparisonSummary(roundId: string) {
    const response = await api.get<AssessmentRoundComparisonSummary>(`/assessment-rounds/${roundId}/comparison-summary`);
    return response.data;
  },
};
