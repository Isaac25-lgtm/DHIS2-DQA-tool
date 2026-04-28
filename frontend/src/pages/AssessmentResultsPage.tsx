import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, PlayCircle, Sparkles } from "lucide-react";
import { useParams } from "react-router-dom";
import { ComparisonResultsTable } from "../components/comparison/ComparisonResultsTable";
import { CorrectiveActionTable } from "../components/corrective-actions/CorrectiveActionTable";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { comparisonService } from "../services/comparisonService";
import { correctiveActionService } from "../services/correctiveActionService";
import type { AssessmentComparisonResults, CorrectiveAction } from "../types";

function severityTone(value: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (value === "EXACT") return "success";
  if (value === "MINOR") return "info";
  if (value === "MODERATE") return "warning";
  if (value === "MAJOR" || value === "CRITICAL" || value === "MISSING") return "danger";
  return "neutral";
}

export function AssessmentResultsPage() {
  const { assessmentFacilityId } = useParams();
  const [results, setResults] = useState<AssessmentComparisonResults | null>(null);
  const [actions, setActions] = useState<CorrectiveAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    if (!assessmentFacilityId) return;
    setLoading(true);
    try {
      const [comparisonResults, correctiveActions] = await Promise.all([
        comparisonService.getAssessmentFacilityComparisonResults(assessmentFacilityId),
        correctiveActionService.listActions(),
      ]);
      setResults(comparisonResults);
      setActions(correctiveActions.filter((item) => item.assessment_facility_id === assessmentFacilityId));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [assessmentFacilityId]);

  if (loading) {
    return <Card title="Assessment Results" subtitle="Loading comparison results."><p className="text-sm text-brand-muted">Loading results...</p></Card>;
  }

  if (!results) {
    return <Card title="Assessment Results" subtitle="No comparison results found."><p className="text-sm text-brand-danger">This assessment does not have comparison data yet.</p></Card>;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-brand-border/70 bg-white px-6 py-5 shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-brand-teal">Assessment results</p>
            <h1 className="mt-2 text-2xl font-bold text-brand-navy">{results.facility.facility_name}</h1>
            <p className="mt-2 text-sm text-brand-muted">
              {results.assessment_round.name} · {results.assessment_round.reporting_period} · {results.assessment_status}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              className="gap-2"
              onClick={async () => {
                if (!assessmentFacilityId) return;
                setRunning(true);
                setMessage(null);
                try {
                  await comparisonService.runAssessmentFacilityComparison(assessmentFacilityId);
                  await load();
                  setMessage("Comparison ran successfully.");
                } finally {
                  setRunning(false);
                }
              }}
            >
              <PlayCircle size={16} />
              {running ? "Running..." : "Run comparison"}
            </Button>
            <Button
              className="gap-2"
              onClick={async () => {
                if (!assessmentFacilityId) return;
                const response = await correctiveActionService.suggestForAssessment(assessmentFacilityId);
                await load();
                setMessage(`Suggested ${response.created} corrective action(s); skipped ${response.skipped}.`);
              }}
            >
              <Sparkles size={16} />
              Suggest corrective actions
            </Button>
          </div>
        </div>
        {message ? <p className="mt-4 text-sm text-brand-teal">{message}</p> : null}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <p className="text-sm text-brand-muted">Overall DQA score</p>
          <p className="mt-2 text-4xl font-extrabold text-brand-navy">{results.dqa_score.score_percent.toFixed(1)}%</p>
          <Badge tone={results.dqa_score.score_category === "EXCELLENT" ? "success" : results.dqa_score.score_category === "POOR" ? "danger" : "warning"} className="mt-3">
            {results.dqa_score.score_category}
          </Badge>
        </Card>
        <Card>
          <p className="text-sm text-brand-muted">Exact matches</p>
          <div className="mt-3 flex items-center gap-3">
            <CheckCircle2 className="text-brand-success" size={20} />
            <span className="text-2xl font-bold text-brand-text">{results.dqa_score.exact_count}</span>
          </div>
        </Card>
        <Card>
          <p className="text-sm text-brand-muted">Major + critical</p>
          <div className="mt-3 flex items-center gap-3">
            <AlertTriangle className="text-brand-danger" size={20} />
            <span className="text-2xl font-bold text-brand-text">{results.dqa_score.major_count + results.dqa_score.critical_count}</span>
          </div>
        </Card>
        <Card>
          <p className="text-sm text-brand-muted">Source completeness</p>
          <p className="mt-2 text-4xl font-extrabold text-brand-navy">{(results.source_document_summary.completeness_rate ?? 0).toFixed(1)}%</p>
        </Card>
      </section>

      <Card title="Comparison results table" subtitle="Register, HMIS 105, and DHIS2 field-time values compared row by row.">
        <ComparisonResultsTable rows={results.comparison_rows} />
      </Card>

      <Card title="Issue counts" subtitle="A quick view of what is driving follow-up.">
        <div className="flex flex-wrap gap-2">
          {Object.entries(results.issue_counts).map(([issueType, count]) => (
            <Badge key={issueType} tone="info">{issueType}: {count}</Badge>
          ))}
          {Object.entries(results.severity_counts).map(([severity, count]) => (
            <Badge key={severity} tone={severityTone(severity)}>{severity}: {count}</Badge>
          ))}
        </div>
      </Card>

      <Card title="Corrective actions" subtitle="Follow-up actions linked to this assessment facility.">
        <CorrectiveActionTable items={actions} />
      </Card>
    </div>
  );
}
