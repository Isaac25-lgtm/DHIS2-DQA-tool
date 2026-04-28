import { useEffect, useState } from "react";
import { Card } from "../components/ui/Card";
import { analyticsService } from "../services/analyticsService";
import { assessmentRoundService } from "../services/assessmentRoundService";
import { IndicatorIssueTable } from "../components/analytics/IndicatorIssueTable";
import type { IndicatorAnalyticsItem } from "../types";

export function IndicatorAnalyticsPage() {
  const [items, setItems] = useState<IndicatorAnalyticsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const rounds = await assessmentRoundService.listRounds();
      if (rounds[0]) {
        setItems(await analyticsService.getRoundIndicators(rounds[0].id));
      }
      setLoading(false);
    };
    void load();
  }, []);

  return (
    <Card title="Indicator Analytics" subtitle="See which HMIS 105 indicators are driving the largest discrepancy burden.">
      {loading ? <p className="text-sm text-brand-muted">Loading indicator analytics...</p> : <IndicatorIssueTable items={items} />}
    </Card>
  );
}
