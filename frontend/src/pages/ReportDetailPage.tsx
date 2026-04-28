import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { FileDown, PencilLine, ShieldCheck } from "lucide-react";
import { ReportPreview } from "../components/reports/ReportPreview";
import { ReportStatusBadge } from "../components/reports/ReportStatusBadge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Textarea } from "../components/ui/Textarea";
import { exportService } from "../services/exportService";
import { reportService } from "../services/reportService";
import { useAuth } from "../hooks/useAuth";
import type { Report } from "../types";

async function extractExportErrorMessage(error: unknown): Promise<string> {
  const candidate = error as { response?: { data?: Blob | { detail?: string } } };
  const payload = candidate.response?.data;
  if (payload instanceof Blob) {
    try {
      const text = await payload.text();
      const parsed = JSON.parse(text) as { detail?: string };
      return parsed.detail ?? "Export is unavailable right now.";
    } catch {
      return "Export is unavailable right now.";
    }
  }
  if (payload && typeof payload === "object" && "detail" in payload) {
    return String(payload.detail ?? "Export is unavailable right now.");
  }
  return "Export is unavailable right now.";
}

export function ReportDetailPage() {
  const { reportId } = useParams();
  const { user } = useAuth();
  const [report, setReport] = useState<Report | null>(null);
  const [editedContent, setEditedContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const loadReport = async () => {
      if (!reportId) {
        return;
      }
      setLoading(true);
      try {
        const response = await reportService.getReport(reportId);
        setReport(response);
        setEditedContent(response.edited_content ?? response.display_content);
      } finally {
        setLoading(false);
      }
    };
    void loadReport();
  }, [reportId]);

  const canEdit = user?.role === "MANAGER";
  const canReview = user?.role === "MANAGER" || user?.role === "REVIEWER";
  const canApprove = user?.role === "MANAGER";
  const canExport = report && (report.status === "APPROVED" || report.status === "EXPORTED");

  const metadata = useMemo(
    () =>
      report
        ? [
            { label: "Type", value: report.report_type.replace(/_/g, " ") },
            { label: "Status", value: report.status },
            { label: "Report template version", value: report.prompt_version },
            { label: "AI provider", value: report.ai_provider ?? "Template fallback / not configured" },
          ]
        : [],
    [report],
  );

  if (loading) {
    return (
      <Card title="Report detail" subtitle="Loading report content.">
        <div className="rounded-2xl bg-brand-surface px-5 py-6 text-sm text-brand-muted">Loading report...</div>
      </Card>
    );
  }

  if (!report) {
    return (
      <Card title="Report detail" subtitle="This report is unavailable.">
        <div className="rounded-2xl bg-brand-surface px-5 py-6 text-sm text-brand-danger">Report not found.</div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card title={report.title} subtitle="Review, edit, approve, and export the generated report.">
        <div className="grid gap-4 md:grid-cols-4">
          {metadata.map((item) => (
            <div key={item.label} className="rounded-2xl bg-brand-surface px-4 py-4">
              <p className="text-xs uppercase tracking-[0.18em] text-brand-muted">{item.label}</p>
              <div className="mt-2">
                {item.label === "Status" ? <ReportStatusBadge status={report.status} /> : <p className="text-sm font-semibold text-brand-text">{item.value}</p>}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {message ? (
        <div className="rounded-2xl border border-brand-border bg-white px-4 py-4 text-sm text-brand-text shadow-soft">{message}</div>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <ReportPreview title="Current preview" content={report.display_content} />

        <Card title="Report editor" subtitle="Managers can refine the draft before review and approval.">
          <Textarea rows={18} value={editedContent} onChange={(event) => setEditedContent(event.target.value)} disabled={!canEdit} />
          <div className="mt-4 flex flex-wrap gap-3">
            <Button
              variant="secondary"
              className="gap-2"
              disabled={!canEdit || saving}
              onClick={async () => {
                if (!reportId) return;
                setSaving(true);
                try {
                  const updated = await reportService.updateReport(reportId, editedContent);
                  setReport(updated);
                  setMessage("Report edits saved.");
                } finally {
                  setSaving(false);
                }
              }}
            >
              <PencilLine size={16} />
              {saving ? "Saving..." : "Save edits"}
            </Button>
            <Button
              variant="secondary"
              className="gap-2"
              disabled={!canReview}
              onClick={async () => {
                if (!reportId) return;
                await reportService.reviewReport(reportId);
                setReport(await reportService.getReport(reportId));
                setMessage("Report marked as reviewed.");
              }}
            >
              <ShieldCheck size={16} />
              Mark reviewed
            </Button>
            <Button
              disabled={!canApprove}
              onClick={async () => {
                if (!reportId) return;
                await reportService.approveReport(reportId);
                setReport(await reportService.getReport(reportId));
                setMessage("Report approved for export.");
              }}
            >
              Approve report
            </Button>
          </div>
        </Card>
      </section>

      <Card title="Export" subtitle="Approved reports can be exported without changing the underlying DQA data.">
        <div className="flex flex-wrap gap-3">
          <Button
            variant="secondary"
            className="gap-2"
            disabled={!canExport}
            onClick={() => reportId && exportService.downloadDocx(reportId).then(() => setMessage("DOCX export started."))}
          >
            <FileDown size={16} />
            Export DOCX
          </Button>
          <Button
            variant="secondary"
            className="gap-2"
            disabled={!canExport}
            onClick={async () => {
              if (!reportId) return;
              try {
                await exportService.downloadPdf(reportId);
                setMessage("PDF export started.");
              } catch (error) {
                setMessage(await extractExportErrorMessage(error));
              }
            }}
          >
            <FileDown size={16} />
            Export PDF
          </Button>
          <Button
            variant="secondary"
            className="gap-2"
            disabled={!canExport}
            onClick={() => reportId && exportService.downloadXlsx(reportId).then(() => setMessage("XLSX export started."))}
          >
            <FileDown size={16} />
            Export XLSX
          </Button>
        </div>
      </Card>
    </div>
  );
}
