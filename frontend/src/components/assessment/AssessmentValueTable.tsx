import { useMemo } from "react";
import { Badge } from "../ui/Badge";
import { Input } from "../ui/Input";
import { Textarea } from "../ui/Textarea";
import type { AssessmentComment, DqaValue, SelectedIndicator } from "../../types";
import {
  calculateDifferenceSummary,
  DifferenceFlagBadge,
  DQA_AMBER_MAX_PERCENT,
  DQA_GREEN_MAX_PERCENT,
  formatPercentDiff,
} from "./DifferenceFlagBadge";

function toDisplayNumber(value: number | null) {
  return value ?? "";
}

type DiffTone = "muted" | "success" | "warning" | "danger";

function getDiffTone(value: number | null): DiffTone {
  if (value === null) return "muted";
  if (value <= DQA_GREEN_MAX_PERCENT) return "success";
  if (value <= DQA_AMBER_MAX_PERCENT) return "warning";
  return "danger";
}

const DIFF_CELL_BG: Record<DiffTone, string> = {
  muted: "bg-brand-surface/40",
  success: "bg-emerald-50",
  warning: "bg-amber-50",
  danger: "bg-red-50",
};

const DIFF_TEXT_COLOR: Record<DiffTone, string> = {
  muted: "text-brand-muted",
  success: "text-emerald-800",
  warning: "text-amber-800",
  danger: "text-red-800",
};

function DifferenceCell({ value }: { value: number | null }) {
  const tone = getDiffTone(value);
  return (
    <span className={`block text-center font-mono-ui text-base font-semibold ${DIFF_TEXT_COLOR[tone]}`}>
      {formatPercentDiff(value)}
    </span>
  );
}

function MetadataLine({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <span className="text-[11px] text-brand-muted">
      <span className="font-medium text-brand-text/70">{label}:</span> {value}
    </span>
  );
}

function IndicatorSummary({ indicator, compact = false }: { indicator: SelectedIndicator; compact?: boolean }) {
  return (
    <div className="min-w-0">
      <p className={`font-semibold leading-snug text-brand-text ${compact ? "text-sm" : "text-[15px]"}`}>
        {indicator.indicator_name}
      </p>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
        <Badge tone="info" className="font-mono-ui">{indicator.hmis_code}</Badge>
        {indicator.is_required ? <Badge tone="success">Required</Badge> : null}
        <MetadataLine label="Register" value={indicator.source_register ?? "Not set"} />
        <MetadataLine label="Group" value={indicator.indicator_group} />
        <MetadataLine label="Combo" value={indicator.category_combo} />
      </div>
    </div>
  );
}

function formatCommentDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function CommentThread({ comments }: { comments: AssessmentComment[] }) {
  if (!comments.length) {
    return (
      <p className="text-xs text-brand-muted">No assessor comments yet for this indicator.</p>
    );
  }
  return (
    <div className="space-y-2">
      {comments.map((comment) => (
        <div key={comment.id} className="rounded-xl border border-brand-border bg-brand-surface/60 px-3 py-2">
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-muted">
            <span>{comment.author_name ?? "Assessor"}</span>
            <span>{formatCommentDate(comment.created_at)}</span>
          </div>
          <p className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-brand-text">{comment.comment_text}</p>
        </div>
      ))}
    </div>
  );
}

function IndicatorCommentBox({
  indicator,
  value,
  comments,
  onChange,
  disabled,
}: {
  indicator: SelectedIndicator;
  value: DqaValue;
  comments: AssessmentComment[];
  onChange: (indicatorId: string, updates: Partial<DqaValue>) => void;
  disabled: boolean;
}) {
  return (
    <div className="mt-3 rounded-[16px] border border-brand-border bg-white/80 p-3">
      <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-brand-muted">Assessor comments</p>
      <CommentThread comments={comments} />
      <Textarea
        rows={2}
        value={value.assessor_comment ?? ""}
        onChange={(event) => onChange(indicator.indicator_id, { assessor_comment: event.target.value || null })}
        disabled={disabled}
        placeholder="Add your comment or revision for this indicator."
        className="mt-3 text-sm"
      />
    </div>
  );
}

type ValueTone = "register" | "hmis" | "dhis2";

const TONE_PALETTE: Record<ValueTone, { label: string; border: string; bg: string; text: string; placeholder: string; focus: string }> = {
  register: {
    label: "text-emerald-900",
    border: "border-emerald-500",
    bg: "bg-emerald-50",
    text: "text-emerald-950",
    placeholder: "placeholder:text-emerald-900/60",
    focus: "focus:border-emerald-700 focus:ring-emerald-200",
  },
  hmis: {
    label: "text-sky-900",
    border: "border-sky-500",
    bg: "bg-sky-50",
    text: "text-sky-950",
    placeholder: "placeholder:text-sky-900/60",
    focus: "focus:border-sky-700 focus:ring-sky-200",
  },
  dhis2: {
    label: "text-emerald-900",
    border: "border-emerald-500",
    bg: "bg-emerald-50",
    text: "text-emerald-900",
    placeholder: "",
    focus: "",
  },
};

function ValueCard({
  label,
  value,
  onChange,
  disabled,
  tone,
  readOnly = false,
}: {
  label: string;
  value: number | null;
  onChange?: (value: number | null) => void;
  disabled?: boolean;
  tone: ValueTone;
  readOnly?: boolean;
}) {
  const palette = TONE_PALETTE[tone];
  const boxBase = `h-[44px] w-full rounded-[10px] border-2 ${palette.border} ${palette.bg} px-3 font-mono-ui text-lg font-bold ${palette.text}`;

  return (
    <label className="block rounded-[14px] border border-brand-border bg-white p-2 shadow-sm">
      <span className={`mb-1 block text-center text-[10px] font-bold uppercase tracking-[0.14em] ${palette.label}`}>
        {label}
      </span>
      {readOnly ? (
        <div className={`${boxBase} flex items-center justify-end`} aria-readonly="true">
          {value ?? "—"}
        </div>
      ) : (
        <Input
          type="number"
          inputMode="numeric"
          min={0}
          placeholder="0"
          value={toDisplayNumber(value)}
          onChange={(event) => onChange?.(event.target.value === "" ? null : Number(event.target.value))}
          disabled={disabled}
          className={`${boxBase} py-0 text-right leading-[40px] ${palette.placeholder} ${palette.focus}`}
        />
      )}
    </label>
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
  comments = [],
  onChange,
  disabled,
}: {
  indicators: SelectedIndicator[];
  values: DqaValue[];
  comments?: AssessmentComment[];
  onChange: (indicatorId: string, updates: Partial<DqaValue>) => void;
  disabled: boolean;
}) {
  const valueMap = useMemo(() => new Map(values.map((item) => [item.indicator_id, item])), [values]);
  const commentsByIndicator = useMemo(() => {
    const next = new Map<string, AssessmentComment[]>();
    comments
      .filter((comment) => comment.comment_type === "INDICATOR" && comment.indicator_id)
      .forEach((comment) => {
        const key = comment.indicator_id as string;
        next.set(key, [...(next.get(key) ?? []), comment]);
      });
    return next;
  }, [comments]);

  return (
    <div className="space-y-4">
      <div className="hidden overflow-x-auto rounded-[22px] border border-brand-border bg-white shadow-soft xl:block">
        <table className="w-full min-w-[1180px] table-fixed divide-y divide-brand-border/70">
          <colgroup>
            <col />
            <col className="w-[160px]" />
            <col className="w-[160px]" />
            <col className="w-[160px]" />
            <col className="w-[140px]" />
            <col className="w-[140px]" />
            <col className="w-[140px]" />
            <col className="w-[110px]" />
          </colgroup>
          <thead>
            <tr className="bg-brand-blue">
              <th rowSpan={2} className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-white/80">
                Indicator, HMIS Code & Source Register
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
            <tr className="divide-x divide-slate-300">
              <th className="bg-amber-50 px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-700">
                HMIS vs Reg
              </th>
              <th className="bg-blue-50 px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">
                DHIS2 vs HMIS
              </th>
              <th className="bg-emerald-50 px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald-700">
                DHIS2 vs Reg
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-300">
            {indicators.map((indicator) => {
              const currentValue = valueMap.get(indicator.indicator_id) ?? fallbackValue(indicator.indicator_id);
              const differenceSummary = calculateDifferenceSummary(
                indicator,
                currentValue.register_value,
                currentValue.hmis105_value,
                currentValue.dhis2_value_at_assessment,
              );

              return (
                <tr key={indicator.id} className="divide-x divide-slate-300 transition hover:bg-brand-surface/70">
                  <td className="px-4 py-4 align-top">
                    <IndicatorSummary indicator={indicator} />
                    <IndicatorCommentBox
                      indicator={indicator}
                      value={currentValue}
                      comments={commentsByIndicator.get(indicator.indicator_id) ?? []}
                      onChange={onChange}
                      disabled={disabled}
                    />
                  </td>
                  <td className="px-4 py-4 align-top">
                    <ValueCard
                      label="Register"
                      value={currentValue.register_value}
                      onChange={(nextValue) =>
                        onChange(indicator.indicator_id, {
                          register_value: nextValue,
                        })
                      }
                      disabled={disabled}
                      tone="register"
                    />
                  </td>
                  <td className="px-4 py-4 align-top">
                    <ValueCard
                      label="HMIS 105"
                      value={currentValue.hmis105_value}
                      onChange={(nextValue) =>
                        onChange(indicator.indicator_id, {
                          hmis105_value: nextValue,
                        })
                      }
                      disabled={disabled}
                      tone="hmis"
                    />
                  </td>
                  <td className="border-l-2 border-emerald-200 px-4 py-4 align-top">
                    <ValueCard
                      label="DHIS 2"
                      value={currentValue.dhis2_value_at_assessment}
                      tone="dhis2"
                      readOnly
                    />
                    <p className="mt-1.5 text-center text-[10px] font-semibold text-emerald-700">{dhis2StatusText(currentValue)}</p>
                    {currentValue.dhis2_error_message ? (
                      <p className="mt-1 text-center text-[10px] text-brand-danger">{currentValue.dhis2_error_message}</p>
                    ) : null}
                  </td>
                  <td className={`px-4 py-4 align-middle ${DIFF_CELL_BG[getDiffTone(differenceSummary.registerHmisPercentDiff)]}`}>
                    <DifferenceCell value={differenceSummary.registerHmisPercentDiff} />
                  </td>
                  <td className={`px-4 py-4 align-middle ${DIFF_CELL_BG[getDiffTone(differenceSummary.hmisDhis2PercentDiff)]}`}>
                    <DifferenceCell value={differenceSummary.hmisDhis2PercentDiff} />
                  </td>
                  <td className={`px-4 py-4 align-middle ${DIFF_CELL_BG[getDiffTone(differenceSummary.registerDhis2PercentDiff)]}`}>
                    <DifferenceCell value={differenceSummary.registerDhis2PercentDiff} />
                  </td>
                  <td className="px-4 py-4 align-middle">
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
            <div key={indicator.id} className="rounded-[18px] border border-brand-border bg-white p-3 shadow-soft">
              <div className="flex items-start justify-between gap-3">
                <IndicatorSummary indicator={indicator} compact />
                <DifferenceFlagBadge summary={differenceSummary} />
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2">
                <ValueCard
                  label="Register"
                  value={currentValue.register_value}
                  onChange={(nextValue) =>
                    onChange(indicator.indicator_id, {
                      register_value: nextValue,
                    })
                  }
                  disabled={disabled}
                  tone="register"
                />
                <ValueCard
                  label="HMIS 105"
                  value={currentValue.hmis105_value}
                  onChange={(nextValue) =>
                    onChange(indicator.indicator_id, {
                      hmis105_value: nextValue,
                    })
                  }
                  disabled={disabled}
                  tone="hmis"
                />
                <ValueCard
                  label="DHIS 2"
                  value={currentValue.dhis2_value_at_assessment}
                  tone="dhis2"
                  readOnly
                />
              </div>
              <p className="mt-1.5 text-center text-[10px] font-semibold text-emerald-700">{dhis2StatusText(currentValue)}</p>

              <div className="mt-3 grid gap-2 rounded-[14px] bg-brand-surface px-3 py-3 text-xs text-brand-text sm:grid-cols-3">
                <p><span className="font-semibold text-brand-navy">HMIS vs Register:</span> {formatPercentDiff(differenceSummary.registerHmisPercentDiff)}</p>
                <p><span className="font-semibold text-brand-navy">DHIS2 vs HMIS 105:</span> {formatPercentDiff(differenceSummary.hmisDhis2PercentDiff)}</p>
                <p><span className="font-semibold text-brand-navy">DHIS2 vs Register:</span> {formatPercentDiff(differenceSummary.registerDhis2PercentDiff)}</p>
              </div>
              <IndicatorCommentBox
                indicator={indicator}
                value={currentValue}
                comments={commentsByIndicator.get(indicator.indicator_id) ?? []}
                onChange={onChange}
                disabled={disabled}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
