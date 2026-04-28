import { useEffect, useState } from "react";
import { Card } from "../components/ui/Card";
import { analyticsService } from "../services/analyticsService";
import { useParams } from "react-router-dom";
import type { AssessmentFacilityAnalyticsSummary } from "../types";

export function FacilityDqaProfilePage() {
  const { assessmentFacilityId } = useParams();
  const [summary, setSummary] = useState<AssessmentFacilityAnalyticsSummary | null>(null);

  useEffect(() => {
    if (!assessmentFacilityId) return;
    void analyticsService.getAssessmentFacilitySummary(assessmentFacilityId).then(setSummary);
  }, [assessmentFacilityId]);

  if (!summary) {
    return <Card title="Facility DQA Profile" subtitle="Loading facility score profile."><p className="text-sm text-brand-muted">Loading facility DQA profile...</p></Card>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <Card title={summary.facility_name} subtitle="Facility-level DQA score summary">
        <p className="text-4xl font-extrabold text-brand-navy">{summary.score_percent.toFixed(1)}%</p>
        <p className="mt-2 text-sm text-brand-muted">{summary.score_category}</p>
      </Card>
      <Card title="Severity counts">
        <div className="space-y-2 text-sm text-brand-text">
          <p>Exact: {summary.exact_count}</p>
          <p>Minor: {summary.minor_count}</p>
          <p>Moderate: {summary.moderate_count}</p>
          <p>Major: {summary.major_count}</p>
          <p>Critical: {summary.critical_count}</p>
          <p>Missing: {summary.missing_count}</p>
        </div>
      </Card>
      <Card title="Corrective actions">
        <p className="text-4xl font-extrabold text-brand-navy">{summary.open_corrective_actions}</p>
        <p className="mt-2 text-sm text-brand-muted">Open actions requiring follow-up.</p>
      </Card>
    </div>
  );
}
