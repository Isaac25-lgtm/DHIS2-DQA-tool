import { useMemo } from "react";
import { Badge } from "../ui/Badge";
import { Input } from "../ui/Input";
import type { DqaValue, SelectedIndicator } from "../../types";
import { calculateDifferenceSummary, DifferenceFlagBadge, formatPercentDiff } from "./DifferenceFlagBadge";

function toDisplayNumber(value: number | null) {
  return value ?? "";
}

function DifferenceCell({ value }: { value: number | null }) {
  return (
    <span className={value !== null && value > 5 ? "font-bold text-brand-danger" : "font-semibold text-brand-text"}>
      {formatPercentDiff(value)}
    </span>
  );
}

function fallbackValue(indicatorId: string): DqaValue {
  return {
    id: indicatorId,
    indicator_id: indicatorId,
    register_value: null,
    hmis105_value: null,
    dhis2_value_at_assessment: null,
    dhis2_extracted_at: null,
    dhis2_api_status: null,
    dhis2_error_message: null,
    dhis2_value_latest: null,
    dhis2_latest_extracted_at: null,
    dhis2_latest_api_status: null,
    dhis2_latest_error_message: null,
    assessor_comment: null,
    manager_comment: null,
    register_vs_hmis_difference: null,
    hmis_vs_dhis2_difference: null,
    register_vs_dhis2_difference: null,
    absolute_discrepancy: null,
    discrepancy_percent: null,
    verification_factor: null,
    issue_type: null,
    severity: null,
    comparison_status: null,
    comparison_notes: null,
    compared_at: null,
    compared_by_user_id: null,
    value_status: "NOT_STARTED",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

export function AssessmentValueTable({
  indicators,
  values,
  onChange,
  disabled,
}: {
  indicators: SelectedIndicator[];
  values: DqaValue[];
  onChange: (indicatorId: string, updates: Partial<DqaValue>) => void;
  disabled: boolean;
}) {
  const valueMap = useMemo(() => new Map(values.map((item) => [item.indicator_id, item])), [values]);

  return (
    <div className="space-y-4">
      <div className="hidden overflow-x-auto rounded-xl border border-brand-border bg-white xl:block">
        <table className="min-w-full divide-y divide-slate-100">
          <thead className="bg-slate-50">
            <tr>
              {[
                "Indicator / Data Element",
                "HMIS Code",
                "Source Register",
                "Register Value",
                "HMIS 105 Value",
                "DHIS2 Value",
                "HMIS vs Register",
                "DHIS2 vs HMIS 105",
                "DHIS2 vs Register",
                "Flag",
              ].map((label) => (
                <th
                  key={label}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-brand-muted"
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {indicators.map((indicator) => {
              const currentValue = valueMap.get(indicator.indicator_id) ?? fallbackValue(indicator.indicator_id);
              const differenceSummary = calculateDifferenceSummary(
                indicator,
                currentValue.register_value,
                currentValue.hmis105_value,
                currentValue.dhis2_value_at_assessment,
              );

              return (
                <tr key={indicator.id}>
                  <td className="max-w-xs px-4 py-4 align-top">
                    <p className="font-semibold text-brand-text">{indicator.indicator_name}</p>
                    <p className="mt-1 text-xs text-brand-muted">{indicator.indicator_group}</p>
                    {indicator.category_combo ? <p className="mt-1 text-xs text-brand-muted">{indicator.category_combo}</p> : null}
                    {indicator.is_required ? <Badge tone="success" className="mt-2">Required</Badge> : null}
                  </td>
                  <td className="px-4 py-4 align-top">
                    <Badge tone="info">{indicator.hmis_code}</Badge>
                  </td>
                  <td className="px-4 py-4 align-top text-sm text-brand-text">
                    {indicator.source_register ?? "Not set"}
                  </td>
                  <td className="px-4 py-4 align-top">
                    <Input
                      type="number"
                      min={0}
                      value={toDisplayNumber(currentValue.register_value)}
                      onChange={(event) =>
                        onChange(indicator.indicator_id, {
                          register_value: event.target.value === "" ? null : Number(event.target.value),
                        })
                      }
                      disabled={disabled}
                    />
                  </td>
                  <td className="px-4 py-4 align-top">
                    <Input
                      type="number"
                      min={0}
                      value={toDisplayNumber(currentValue.hmis105_value)}
                      onChange={(event) =>
                        onChange(indicator.indicator_id, {
                          hmis105_value: event.target.value === "" ? null : Number(event.target.value),
                        })
                      }
                      disabled={disabled}
                    />
                  </td>
                  <td className="px-4 py-4 align-top">
                    <div className="rounded-xl bg-brand-surface px-3 py-2 text-center text-sm font-semibold text-brand-navy">
                      {currentValue.dhis2_value_at_assessment ?? "-"}
                    </div>
                  </td>
                  <td className="px-4 py-4 align-top">
                    <DifferenceCell value={differenceSummary.registerHmisPercentDiff} />
                  </td>
                  <td className="px-4 py-4 align-top">
                    <DifferenceCell value={differenceSummary.hmisDhis2PercentDiff} />
                  </td>
                  <td className="px-4 py-4 align-top">
                    <DifferenceCell value={differenceSummary.registerDhis2PercentDiff} />
                  </td>
                  <td className="px-4 py-4 align-top">
                    <DifferenceFlagBadge summary={differenceSummary} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="space-y-4 xl:hidden">
        {indicators.map((indicator) => {
          const currentValue = valueMap.get(indicator.indicator_id) ?? fallbackValue(indicator.indicator_id);
          const differenceSummary = calculateDifferenceSummary(
            indicator,
            currentValue.register_value,
            currentValue.hmis105_value,
            currentValue.dhis2_value_at_assessment,
          );

          return (
            <div key={indicator.id} className="rounded-2xl border border-brand-border bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-brand-text">{indicator.indicator_name}</p>
                  <p className="mt-1 text-sm text-brand-muted">{indicator.hmis_code}</p>
                  <p className="mt-1 text-xs text-brand-muted">{indicator.source_register ?? "Source register not set"}</p>
                  <p className="mt-1 text-xs text-brand-muted">{indicator.indicator_group}{indicator.category_combo ? ` - ${indicator.category_combo}` : ""}</p>
                </div>
                <DifferenceFlagBadge summary={differenceSummary} />
              </div>

              <div className="mt-4 grid gap-3">
                <label className="space-y-1">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-muted">Register Value</span>
                  <Input
                    type="number"
                    min={0}
                    value={toDisplayNumber(currentValue.register_value)}
                    onChange={(event) =>
                      onChange(indicator.indicator_id, {
                        register_value: event.target.value === "" ? null : Number(event.target.value),
                      })
                    }
                    disabled={disabled}
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-muted">HMIS 105 Value</span>
                  <Input
                    type="number"
                    min={0}
                    value={toDisplayNumber(currentValue.hmis105_value)}
                    onChange={(event) =>
                      onChange(indicator.indicator_id, {
                        hmis105_value: event.target.value === "" ? null : Number(event.target.value),
                      })
                    }
                    disabled={disabled}
                  />
                </label>
              </div>

              <div className="mt-4 grid gap-3 rounded-xl bg-brand-surface px-3 py-3 text-sm text-brand-text sm:grid-cols-2">
                <p><span className="font-semibold text-brand-navy">DHIS2:</span> {currentValue.dhis2_value_at_assessment ?? "-"}</p>
                <p><span className="font-semibold text-brand-navy">HMIS vs Register:</span> {formatPercentDiff(differenceSummary.registerHmisPercentDiff)}</p>
                <p><span className="font-semibold text-brand-navy">DHIS2 vs HMIS 105:</span> {formatPercentDiff(differenceSummary.hmisDhis2PercentDiff)}</p>
                <p><span className="font-semibold text-brand-navy">DHIS2 vs Register:</span> {formatPercentDiff(differenceSummary.registerDhis2PercentDiff)}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
