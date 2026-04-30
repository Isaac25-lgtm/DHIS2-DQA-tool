import { api } from "./api";
import type { Report, ReportGeneratePayload } from "../types";

const REPORT_GENERATION_TIMEOUT_MS = 180000;

export const reportService = {
  async listReports(filters?: {
    assessment_round_id?: string;
    assessment_facility_id?: string;
    report_type?: string;
    status_value?: string;
  }) {
    const { data } = await api.get<Report[]>("/reports", { params: filters });
    return data;
  },
  async generateReport(payload: ReportGeneratePayload) {
    const { data } = await api.post<Report>("/reports/generate", payload, {
      timeout: REPORT_GENERATION_TIMEOUT_MS,
    });
    return data;
  },
  async getReport(reportId: string) {
    const { data } = await api.get<Report>(`/reports/${reportId}`);
    return data;
  },
  async updateReport(reportId: string, editedContent: string) {
    const { data } = await api.put<Report>(`/reports/${reportId}`, { edited_content: editedContent });
    return data;
  },
  async reviewReport(reportId: string) {
    const { data } = await api.post(`/reports/${reportId}/review`);
    return data;
  },
  async approveReport(reportId: string) {
    const { data } = await api.post(`/reports/${reportId}/approve`);
    return data;
  },
  async archiveReport(reportId: string) {
    const { data } = await api.post(`/reports/${reportId}/archive`);
    return data;
  },
};
