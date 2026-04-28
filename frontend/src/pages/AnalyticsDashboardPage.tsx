import { useEffect, useMemo, useState } from "react";
import { DiscrepancyTypeChart } from "../components/analytics/DiscrepancyTypeChart";
import { DqaHeatmap } from "../components/analytics/DqaHeatmap";
import { FacilityScoreTable } from "../components/analytics/FacilityScoreTable";
import { IndicatorIssueTable } from "../components/analytics/IndicatorIssueTable";
import { SourceDocumentChart } from "../components/analytics/SourceDocumentChart";
import { SummaryMetricCard } from "../components/analytics/SummaryMetricCard";
import { Card } from "../components/ui/Card";
import { analyticsService } from "../services/analyticsService";
import { assessmentRoundService } from "../services/assessmentRoundService";
import type {
  AnalyticsSummary,
  FacilityAnalyticsItem,
  HeatmapCell,
  IndicatorAnalyticsItem,
  SourceDocumentAnalyticsItem,
} from "../types";

export function AnalyticsDashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [facilityItems, setFacilityItems] = useState<FacilityAnalyticsItem[]>([]);
  const [indicatorItems, setIndicatorItems] = useState<IndicatorAnalyticsItem[]>([]);
  const [sourceDocumentItems, setSourceDocumentItems] = useState<SourceDocumentAnalyticsItem[]>([]);
  const [heatmapCells, setHeatmapCells] = useState<HeatmapCell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const rounds = await assessmentRoundService.listRounds();
        const selectedRoundId = rounds[0]?.id;
        const [overallSummary, facilities, indicators, documents, heatmap] = await Promise.all([
          analyticsService.getOverallSummary(),
          selectedRoundId ? analyticsService.getRoundFacilities(selectedRoundId) : Promise.resolve([]),
          selectedRoundId ? analyticsService.getRoundIndicators(selectedRoundId) : Promise.resolve([]),
          selectedRoundId ? analyticsService.getRoundSourceDocuments(selectedRoundId) : Promise.resolve([]),
          selectedRoundId ? analyticsService.getRoundHeatmap(selectedRoundId) : Promise.resolve([]),
        ]);
        setSummary(overallSummary);
        setFacilityItems(facilities);
        setIndicatorItems(indicators);
        setSourceDocumentItems(documents);
        setHeatmapCells(heatmap);
      } catch {
        setError("Unable to load analytics right now.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const discrepancyChartData = useMemo(
    () =>
      summary
        ? [
            { name: "Register to HMIS", value: summary.register_to_hmis_error_count },
            { name: "DHIS2 entry", value: summary.dhis2_entry_error_count },
            { name: "Multiple stage", value: summary.multiple_stage_error_count },
            { name: "Missing", value: summary.missing_value_count },
            { name: "Critical", value: summary.critical_discrepancy_count },
          ]
        : [],
    [summary],
  );

  if (loading) {
    return <Card title="Analytics" subtitle="Loading data quality analytics."><p className="text-sm text-brand-muted">Loading analytics...</p></Card>;
  }

  if (error || !summary) {
    return <Card title="Analytics unavailable" subtitle="Analytics could not be loaded."><p className="text-sm text-brand-danger">{error ?? "No analytics data available."}</p></Card>;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryMetricCard title="Facilities assessed" value={summary.facilities_assessed} helper="Submitted or reviewed assignments." tone="success" />
        <SummaryMetricCard title="Facilities pending" value={summary.facilities_pending} helper="Assignments still awaiting review-ready comparison." tone="warning" />
        <SummaryMetricCard title="Exact match rate" value={`${summary.exact_match_rate.toFixed(1)}%`} helper="Comparison rows with no discrepancy." tone="info" />
        <SummaryMetricCard title="Major discrepancies" value={`${summary.major_discrepancy_rate.toFixed(1)}%`} helper="Major and critical discrepancies across compared rows." tone="danger" />
        <SummaryMetricCard title="Critical discrepancies" value={summary.critical_discrepancy_count} tone="danger" />
        <SummaryMetricCard title="Open corrective actions" value={summary.open_corrective_actions} tone="warning" />
        <SummaryMetricCard title="Overdue corrective actions" value={summary.overdue_corrective_actions} tone="danger" />
        <SummaryMetricCard title="Source document completeness" value={`${summary.source_document_completeness_rate.toFixed(1)}%`} tone="info" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card title="Facility DQA ranking" subtitle="Highest score at the top.">
          <FacilityScoreTable items={facilityItems} />
        </Card>
        <Card title="Discrepancy type distribution" subtitle="How discrepancy patterns are clustering across the current data.">
          <DiscrepancyTypeChart data={discrepancyChartData} />
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card title="Indicator discrepancy ranking" subtitle="Indicators with the weakest data quality patterns rise to the top.">
          <IndicatorIssueTable items={indicatorItems} />
        </Card>
        <Card title="Source document completeness" subtitle="Availability and completeness rates by source document group.">
          <SourceDocumentChart items={sourceDocumentItems} />
        </Card>
      </section>

      <Card title="Facility by indicator heatmap" subtitle="Severity is color-coded from exact matches to missing or critical issues.">
        <DqaHeatmap cells={heatmapCells} />
      </Card>
    </div>
  );
}
