import { api } from "./api";

const REPORT_EXPORT_TIMEOUT_MS = 180000;

async function downloadBlob(url: string, fallbackFileName: string) {
  const response = await api.get(url, {
    responseType: "blob",
    timeout: REPORT_EXPORT_TIMEOUT_MS,
  });
  const fileName =
    response.headers["content-disposition"]?.match(/filename=\"?([^"]+)\"?/)?.[1] ??
    fallbackFileName;
  const blobUrl = window.URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export const exportService = {
  downloadDocx(reportId: string) {
    return downloadBlob(`/reports/${reportId}/export/docx`, "report.docx");
  },
  downloadPdf(reportId: string) {
    return downloadBlob(`/reports/${reportId}/export/pdf`, "report.pdf");
  },
  downloadXlsx(reportId: string) {
    return downloadBlob(`/reports/${reportId}/export/xlsx`, "report.xlsx");
  },
};
