import { useMemo } from "react";
import { Badge } from "../ui/Badge";
import { Input } from "../ui/Input";
import type { DqaValue, SelectedIndicator } from "../../types";
import { calculateDifferenceSummary, DifferenceFlagBadge, formatPercentDiff } from "./DifferenceFlagBadge";

function toDisplayNumber(value: number | null) {
  return value ?? "";
}

function DifferenceCell({ value }: { value: number | null }) {
  const cappedWidth = value === null ? 0 : Math.min(Math.abs(value) * 8, 100);
  const toneClass =
    value === null
      ? "text-brand-muted"
      : value === 0
        ? "text-brand-success"
        : value <= 5
          ? "text-brand-warning"
          : "text-brand-danger";
  const barClass =
    value === null
      ? "bg-brand-border"
      : value === 0
        ? "bg-brand-success"
        : value <= 5
          ? "bg-brand-warning"
          : "bg-brand-danger";

  return (
    <div className="min-w-28">
      <span className={`font-mono-ui text-sm font-semibold ${toneClass}`}>{formatPercentDiff(value)}</span>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-brand-surface">
        <div className={`h-full rounded-full ${barClass}`} style={{ width: `${cappedWidth}%` }} />
      </div>
    </div>
  );
}

function dhis2StatusText(value: DqaValue) {
  if (value.dhis2_value_at_assessment !== null && value.dhis2_value_at_assessment !== undefined) {
    if (value.dhis2_api_status === "ERROR" || value.dhis2_api_status === "NOT_CONFIGURED") {
      return "Manager synced earlier; latest retry failed";
    }
    return "Manager synced";
  }
  if (value.dhis2_api_status === "NOT_CONFIGURED") {
    return "DHIS2 setup missing";
  }
  if (value.dhis2_api_status === "ERROR") {
    return "Sync failed, value preserved if previously synced";
  }
  if (value.dhis2_api_status === "NO_DATA") {
    return "No DHIS2 data returned";
  }
  return "Waiting for manager sync";
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
      <div className="hidden overflow-x-auto rounded-[22px] border border-brand-border bg-white shadow-soft xl:block">
        <table className="min-w-[1180px] divide-y divide-brand-border/70">
          <thead>
            <tr className="bg-brand-blue">
              <th rowSpan={2} className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-white/80">
                Indicator / Data Element
              </th>
              <th rowSpan={2} className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-white/80">
                HMIS Code
              </th>
              <th rowSpan={2} className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-white/80">
                Source Register
              </th>
              <th rowSpan={2} className="bg-emerald-950/40 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-50">
                Register Value
              </th>
              <th rowSpan={2} className="bg-sky-950/40 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-50">
                HMIS 105 Value
              </th>
              <th rowSpan={2} className="border-l-2 border-white/70 bg-emerald-900 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-50">
                DHIS2 Value
              </th>
              <th colSpan={3} className="bg-brand-navy px-4 py-2 text-center text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                % Differences (auto-calculated)
              </th>
              <th rowSpan={2} className="bg-purple-950/70 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-purple-50">
                Flag
              </th>
            </tr>
            <tr>
              <th className="bg-amber-50 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-700">
                HMIS vs Reg
              </th>
              <th className="bg-blue-50 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">
                DHIS2 vs HMIS
              </th>
              <th className="bg-emerald-50 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald-700">
                DHIS2 vs Reg
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-brand-border/70">
            {indicators.map((indicator) => {
              const currentValue = valueMap.get(indicator.indicator_id) ?? fallbackValue(indicator.indicator_id);
              const differenceSummary = calculateDifferenceSummary(
                indicator,
                currentValue.register_value,
                currentValue.hmis105_value,
                currentValue.dhis2_value_at_assessment,
              );

              return (
                <tr key={indicator.id} className="transition hover:bg-brand-surface/70">
                  <td className="max-w-xs px-4 py-4 align-top">
                    <p className="font-semibold text-brand-text">{indicator.indicator_name}</p>
                    <p className="mt-1 text-xs text-brand-muted">{indicator.indicator_group}</p>
                    {indicator.category_combo ? <p className="mt-1 text-xs text-brand-muted">{indicator.category_combo}</p> : null}
                    {indicator.is_required ? <Badge tone="success" className="mt-2">Required</Badge> : null}
                  </td>
                  <td className="px-4 py-4 align-top">
                    <Badge tone="info" className="font-mono-ui">{indicator.hmis_code}</Badge>
                  </td>
                  <td className="px-4 py-4 align-top text-sm text-brand-text">
                    {indicator.source_register ?? "Not set"}
                  </td>
                  <td className="px-4 py-4 align-top">
                    <Input
                      type="number"
                      inputMode="numeric"
                      min={0}
                      value={toDisplayNumber(currentValue.register_value)}
                      onChange={(event) =>
                        onChange(indicator.indicator_id, {
                          register_value: event.target.value === "" ? null : Number(event.target.value),
                        })
                      }
                      disabled={disabled}
                      className="bg-emerald-50 font-mono-ui text-lg font-bold text-emerald-950 placeholder:text-emerald-900/40"
                    />
                  </td>
                  <td className="px-4 py-4 align-top">
                    <Input
                      type="number"
                      inputMode="numeric"
                      min={0}
                      value={toDisplayNumber(currentValue.hmis105_value)}
                      onChange={(event) =>
                        onChange(indicator.indicator_id, {
                          hmis105_value: event.target.value === "" ? null : Number(event.target.value),
                        })
                      }
                      disabled={disabled}
                      className="border-2 border-sky-300 bg-sky-50 font-mono-ui text-lg font-bold text-sky-950 shadow-inner placeholder:text-sky-900/40 focus:border-sky-500 focus:ring-sky-200"
                    />
                  </td>
                  <td className="border-l-2 border-emerald-200 bg-emerald-50/45 px-4 py-4 align-top">
                    <div className="rounded-[14px] border border-emerald-200 bg-emerald-50 px-3 py-2 text-center font-mono-ui text-lg font-bold text-emerald-800">
                      {currentValue.dhis2_value_at_assessment ?? "-"}
                    </div>
                    <p className="mt-1 text-center text-[10px] font-semibold text-emerald-700">{dhis2StatusText(currentValue)}</p>
                    {currentValue.dhis2_error_message ? (
                      <p className="mt-1 max-w-40 text-center text-[10px] text-brand-danger">{currentValue.dhis2_error_message}</p>
                    ) : null}
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
            <div key={indicator.id} className="rounded-[22px] border border-brand-border bg-white p-4 shadow-soft">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-brand-text">{indicator.indicator_name}</p>
                  <p className="font-mono-ui mt-1 text-sm text-brand-teal">{indicator.hmis_code}</p>
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
                    inputMode="numeric"
                    min={0}
                    value={toDisplayNumber(currentValue.register_value)}
                    onChange={(event) =>
                      onChange(indicator.indicator_id, {
                        register_value: event.target.value === "" ? null : Number(event.target.value),
                      })
                    }
                    disabled={disabled}
                    className="bg-emerald-50 font-mono-ui text-lg font-bold text-emerald-950"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-muted">HMIS 105 Value</span>
                  <Input
                    type="number"
                    inputMode="numeric"
                    min={0}
                    value={toDisplayNumber(currentValue.hmis105_value)}
                    onChange={(event) =>
                      onChange(indicator.indicator_id, {
                        hmis105_value: event.target.value === "" ? null : Number(event.target.value),
                      })
                    }
                    disabled={disabled}
                    className="border-2 border-sky-300 bg-sky-50 font-mono-ui text-lg font-bold text-sky-950"
                  />
                </label>
              </div>

              <div className="mt-4 grid gap-3 rounded-[18px] bg-brand-surface px-3 py-3 text-sm text-brand-text sm:grid-cols-2">
                <p className="rounded-[14px] border border-emerald-200 bg-emerald-50 px-3 py-2">
                  <span className="font-semibold text-emerald-800">DHIS2:</span> {currentValue.dhis2_value_at_assessment ?? "-"}
                  <span className="mt-1 block text-xs text-emerald-700">{dhis2StatusText(currentValue)}</span>
                </p>
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
