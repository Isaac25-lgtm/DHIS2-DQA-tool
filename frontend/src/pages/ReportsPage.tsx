import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";
import { Card } from "../components/ui/Card";
import { ReportListTable } from "../components/reports/ReportListTable";
import { reportService } from "../services/reportService";
import type { Report } from "../types";

export function ReportsPage() {
  const navigate = useNavigate();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

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
      <Card title="Report Archive" subtitle="Review, reopen, approve, export, or download reports generated from assessment submissions.">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-3 rounded-2xl bg-brand-surface px-4 py-3 text-sm text-brand-text">
            <FileText size={18} className="text-brand-teal" />
            {loading ? "Loading report history..." : `${reports.length} reports available`}
          </div>
          <p className="text-sm text-brand-muted">
            Generate new reports from Submissions after selecting the relevant assessment round.
          </p>
        </div>
      </Card>

      <Card title="Generated reports" subtitle="Reports stay here after they are generated from assessment submissions.">
        <ReportListTable reports={reports} onOpen={(reportId) => navigate(`/reports/${reportId}`)} />
      </Card>
    </div>
  );
}
