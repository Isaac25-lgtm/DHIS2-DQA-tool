import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { ReportGeneratorForm } from "../components/reports/ReportGeneratorForm";
import { ReportPreview } from "../components/reports/ReportPreview";
import { assessmentRoundService } from "../services/assessmentRoundService";
import { reportService } from "../services/reportService";
import type { AssessmentFacilityAssignment, AssessmentRoundListItem, Report, ReportGeneratePayload, ReportType } from "../types";

export function ReportGeneratorPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [rounds, setRounds] = useState<AssessmentRoundListItem[]>([]);
  const [facilities, setFacilities] = useState<AssessmentFacilityAssignment[]>([]);
  const [generatedReport, setGeneratedReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);

  const initialType = (searchParams.get("type") as ReportType | null) ?? "FACILITY_DQA_REPORT";
  const [formValue, setFormValue] = useState<ReportGeneratePayload>({
    report_type: initialType,
    include_comments: false,
    assessment_round_id: null,
    assessment_facility_id: null,
  });

  useEffect(() => {
    const loadRounds = async () => {
      setPageLoading(true);
      try {
        setRounds(await assessmentRoundService.listRounds());
      } finally {
        setPageLoading(false);
      }
    };
    void loadRounds();
  }, []);

  useEffect(() => {
    const loadFacilities = async () => {
      if (!formValue.assessment_round_id) {
        setFacilities([]);
        return;
      }
      const round = await assessmentRoundService.getRound(formValue.assessment_round_id);
      setFacilities(round.selected_facilities);
    };
    void loadFacilities();
  }, [formValue.assessment_round_id]);

  const selectedRound = useMemo(
    () => rounds.find((item) => item.id === formValue.assessment_round_id) ?? null,
    [formValue.assessment_round_id, rounds],
  );

  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <Card title="Generate report" subtitle="Prepare a structured report input and generate a draft report for review.">
        {pageLoading ? (
          <div className="rounded-2xl bg-brand-surface px-4 py-5 text-sm text-brand-muted">Loading assessment rounds...</div>
        ) : (
          <ReportGeneratorForm
            value={formValue}
            rounds={rounds}
            facilities={facilities}
            onChange={(updates) => setFormValue((current) => ({ ...current, ...updates }))}
            loading={loading}
            onSubmit={async () => {
              setLoading(true);
              try {
                const report = await reportService.generateReport(formValue);
                setGeneratedReport(report);
              } finally {
                setLoading(false);
              }
            }}
          />
        )}
        {selectedRound ? (
          <div className="mt-4 rounded-2xl border border-brand-border bg-white px-4 py-4 text-sm text-brand-muted">
            Generating against <span className="font-semibold text-brand-text">{selectedRound.name}</span> ({selectedRound.reporting_period}).
          </div>
        ) : null}
      </Card>

      {generatedReport ? (
        <div className="space-y-4">
          <ReportPreview title={generatedReport.title} content={generatedReport.display_content} />
          <div className="flex justify-end">
            <button
              type="button"
              className="rounded-2xl bg-brand-navy px-4 py-3 text-sm font-semibold text-white shadow-soft"
              onClick={() => navigate(`/reports/${generatedReport.id}`)}
            >
              Open full report
            </button>
          </div>
        </div>
      ) : (
        <Card title="Preview" subtitle="The generated report preview will appear here.">
          <div className="rounded-2xl bg-brand-surface px-5 py-6 text-sm text-brand-muted">
            Generate a report to preview its draft narrative here.
          </div>
        </Card>
      )}
    </div>
  );
}
