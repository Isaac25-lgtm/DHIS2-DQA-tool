import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, PlusCircle } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { ReportListTable } from "../components/reports/ReportListTable";
import { ReportTypeCard } from "../components/reports/ReportTypeCard";
import { useAuth } from "../hooks/useAuth";
import { reportService } from "../services/reportService";
import type { Report, ReportType } from "../types";

const reportCards: Array<{ reportType: ReportType; title: string; description: string }> = [
  {
    reportType: "FACILITY_DQA_REPORT",
    title: "Facility DQA Report",
    description: "Narrative report for one assessed facility, including comparison findings and corrective actions.",
  },
  {
    reportType: "CONSOLIDATED_UCMB_DQA_REPORT",
    title: "Consolidated UCMB DQA Report",
    description: "Cross-facility summary of scores, discrepancy patterns, and source-document quality.",
  },
  {
    reportType: "CORRECTIVE_ACTION_REPORT",
    title: "Corrective Action Report",
    description: "Operational report focused on open, overdue, resolved, and verified actions.",
  },
  {
    reportType: "EXECUTIVE_SUMMARY",
    title: "Executive Summary",
    description: "Concise management-facing summary of key findings and high-risk follow-up priorities.",
  },
];

export function ReportsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState<ReportType>("FACILITY_DQA_REPORT");
  const canGenerate = user?.role === "MANAGER";

  useEffect(() => {
    const loadReports = async () => {
      setLoading(true);
      try {
        setReports(await reportService.listReports());
      } finally {
        setLoading(false);
      }
    };

    void loadReports();
  }, []);

  return (
    <div className="space-y-6">
      <Card title="Reports" subtitle="Generate formal UCMB DQA reports, review them, and export approved outputs.">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3 rounded-2xl bg-brand-surface px-4 py-3 text-sm text-brand-text">
            <FileText size={18} className="text-brand-teal" />
            {loading ? "Loading report history..." : `${reports.length} reports available`}
          </div>
          {canGenerate ? (
            <Button className="gap-2" onClick={() => navigate("/reports/generate")}>
              <PlusCircle size={16} />
              Generate report
            </Button>
          ) : null}
        </div>
      </Card>

      {canGenerate ? (
        <section className="grid gap-4 xl:grid-cols-2">
          {reportCards.map((item) => (
            <ReportTypeCard
              key={item.reportType}
              {...item}
              selected={selectedType === item.reportType}
              onSelect={(reportType) => {
                setSelectedType(reportType);
                navigate(`/reports/generate?type=${reportType}`);
              }}
            />
          ))}
        </section>
      ) : null}

      <Card title="Generated reports" subtitle="Reports stay in draft/generated state until reviewed and approved.">
        <ReportListTable reports={reports} onOpen={(reportId) => navigate(`/reports/${reportId}`)} />
      </Card>
    </div>
  );
}
