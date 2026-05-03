import { X } from "lucide-react";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import type { SubmissionDetail } from "../../types";

interface SeverityRule {
  weight: number | null;
  description: string;
  tone: "success" | "warning" | "danger" | "neutral";
}

const SEVERITY_RULES: Record<string, SeverityRule> = {
  EXACT: { weight: 1.0, description: "All sources match exactly", tone: "success" },
  MINOR: { weight: 0.75, description: "Within tolerance (≤5%)", tone: "success" },
  MODERATE: { weight: 0.5, description: "Difference 5%–10%", tone: "warning" },
  MAJOR: { weight: 0.0, description: "Difference > 10%", tone: "danger" },
  CRITICAL: { weight: 0.0, description: "High-risk indicator with any spread", tone: "danger" },
  MISSING: { weight: 0.0, description: "One or more values missing", tone: "neutral" },
  NOT_APPLICABLE: { weight: null, description: "Excluded from score", tone: "neutral" },
};

function ruleFor(severity: string | null): SeverityRule {
  if (!severity) return SEVERITY_RULES.NOT_APPLICABLE;
  return SEVERITY_RULES[severity] ?? SEVERITY_RULES.NOT_APPLICABLE;
}

export function ScoreBreakdownModal({
  detail,
  onClose,
}: {
  detail: SubmissionDetail;
  onClose: () => void;
}) {
  const rows = detail.values.map((value) => {
    const rule = ruleFor(value.severity);
    return { value, rule };
  });

  const counted = rows.filter((row) => row.rule.weight !== null);
  const earnedPoints = counted.reduce((sum, row) => sum + (row.rule.weight ?? 0), 0);
  const possiblePoints = counted.length;
  const localScore = possiblePoints > 0 ? (earnedPoints / possiblePoints) * 100 : 0;
  const backendScore = detail.summary.dqa_score;
  const scoreMatchesLocal = Math.abs(localScore - backendScore) < 0.5;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-brand-navy/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-[24px] bg-white shadow-panel"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 bg-brand-navy px-6 py-4 text-white">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-emerald-100">
              How this score was calculated
            </p>
            <h2 className="mt-1 font-display text-xl font-semibold">{detail.summary.facility_name}</h2>
            <p className="mt-1 text-xs text-white/70">
              {detail.summary.assessment_round_name} · {detail.summary.reporting_period}
            </p>
          </div>
          <Button variant="ghost" className="text-white hover:bg-white/10" onClick={onClose}>
            <X size={18} />
          </Button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          <section className="rounded-[14px] border border-brand-border bg-brand-surface px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">The formula</p>
            <p className="mt-2 font-mono-ui text-sm text-brand-text">
              score = ( Σ weights of all counted rows ) ÷ ( count of counted rows ) × 100
            </p>
            <p className="mt-2 text-xs text-brand-muted">
              Each row contributes a weight based on its severity. Rows tagged <span className="font-semibold">NOT_APPLICABLE</span> are excluded from both the numerator and the denominator.
            </p>
          </section>

          <section>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">Severity weights</p>
            <div className="overflow-hidden rounded-[14px] border border-brand-border">
              <table className="w-full text-sm">
                <thead className="bg-brand-surface text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-muted">
                  <tr>
                    <th className="px-3 py-2">Severity</th>
                    <th className="px-3 py-2 text-right">Weight</th>
                    <th className="px-3 py-2">Meaning</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-border/70">
                  {Object.entries(SEVERITY_RULES).map(([key, rule]) => (
                    <tr key={key}>
                      <td className="px-3 py-2">
                        <Badge tone={rule.tone}>{key}</Badge>
                      </td>
                      <td className="px-3 py-2 text-right font-mono-ui font-semibold text-brand-text">
                        {rule.weight === null ? "—" : rule.weight.toFixed(2)}
                      </td>
                      <td className="px-3 py-2 text-brand-muted">{rule.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted">
              Per-indicator breakdown ({rows.length} rows)
            </p>
            <div className="overflow-hidden rounded-[14px] border border-brand-border">
              <table className="w-full text-sm">
                <thead className="bg-brand-surface text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-muted">
                  <tr>
                    <th className="px-3 py-2">Indicator</th>
                    <th className="px-3 py-2">Severity</th>
                    <th className="px-3 py-2 text-right">Points earned</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-border/70">
                  {rows.map(({ value, rule }) => (
                    <tr key={value.indicator_id}>
                      <td className="px-3 py-2">
                        <p className="font-semibold text-brand-text">{value.indicator_name}</p>
                        <p className="font-mono-ui text-[10px] text-brand-teal">{value.hmis_code}</p>
                      </td>
                      <td className="px-3 py-2">
                        <Badge tone={rule.tone}>{value.severity ?? "NOT_APPLICABLE"}</Badge>
                      </td>
                      <td className="px-3 py-2 text-right font-mono-ui font-semibold text-brand-text">
                        {rule.weight === null ? (
                          <span className="text-brand-muted">excluded</span>
                        ) : (
                          `${rule.weight.toFixed(2)} / 1.00`
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-[14px] border-2 border-brand-teal/40 bg-emerald-50 px-4 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-900">Calculation</p>
            <div className="mt-2 space-y-1 font-mono-ui text-sm text-brand-text">
              <p>Total points earned: <span className="font-semibold">{earnedPoints.toFixed(2)}</span></p>
              <p>Total counted rows: <span className="font-semibold">{possiblePoints}</span></p>
              <p>
                Local score (this view): {earnedPoints.toFixed(2)} ÷ {possiblePoints || 0} × 100 ={" "}
                <span className="font-semibold text-emerald-900">{localScore.toFixed(1)}%</span>
              </p>
              <p className="pt-1">
                Recorded score: <span className="font-semibold text-emerald-900">{backendScore.toFixed(1)}%</span>{" "}
                · Category: <span className="font-semibold">{detail.summary.score_category}</span>
              </p>
            </div>
            {!scoreMatchesLocal ? (
              <p className="mt-3 text-xs text-brand-muted">
                The local sum here can differ from the recorded score because the backend counts only required indicators of the round. This view counts every submitted row.
              </p>
            ) : null}
          </section>
        </div>
      </div>
    </div>
  );
}
