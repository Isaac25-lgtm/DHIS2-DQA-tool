import { Badge } from "../ui/Badge";
import type { SelectedIndicator } from "../../types";

export const DQA_GREEN_MAX_PERCENT = 5;
export const DQA_AMBER_MAX_PERCENT = 20;

export interface DifferenceSummary {
  registerHmisPercentDiff: number | null;
  hmisDhis2PercentDiff: number | null;
  registerDhis2PercentDiff: number | null;
  maxPercentDiff: number | null;
  label: "Match" | "Within tolerance" | "Moderate variance" | "Above tolerance" | "Incomplete" | "Critical" | "High variance";
  tone: "success" | "warning" | "danger" | "neutral";
}

function percentDiff(referenceValue: number | null, comparisonValue: number | null) {
  if (referenceValue === null || comparisonValue === null) {
    return null;
  }
  if (referenceValue === 0 && comparisonValue === 0) {
    return 0;
  }
  if (referenceValue === 0 && comparisonValue > 0) {
    return null;
  }
  return Math.abs(comparisonValue - referenceValue) / Math.abs(referenceValue) * 100;
}

function hasDeathOrHighRiskDifference(
  indicator: SelectedIndicator,
  registerValue: number | null,
  hmis105Value: number | null,
  dhis2Value: number | null,
) {
  if (!indicator.is_death_indicator) {
    return false;
  }
  const values = [registerValue, hmis105Value, dhis2Value].filter((value): value is number => value !== null);
  if (values.length < 2) {
    return false;
  }
  return Math.max(...values) - Math.min(...values) >= 1;
}

export function calculateDifferenceSummary(
  indicator: SelectedIndicator,
  registerValue: number | null,
  hmis105Value: number | null,
  dhis2Value: number | null,
): DifferenceSummary {
  const registerHmisPercentDiff = percentDiff(registerValue, hmis105Value);
  const hmisDhis2PercentDiff = percentDiff(hmis105Value, dhis2Value);
  const registerDhis2PercentDiff = percentDiff(registerValue, dhis2Value);
  const validDiffs = [registerHmisPercentDiff, hmisDhis2PercentDiff, registerDhis2PercentDiff].filter(
    (value): value is number => value !== null,
  );

  if (registerValue === null || hmis105Value === null || dhis2Value === null) {
    if (hasDeathOrHighRiskDifference(indicator, registerValue, hmis105Value, dhis2Value)) {
      return {
        registerHmisPercentDiff,
        hmisDhis2PercentDiff,
        registerDhis2PercentDiff,
        maxPercentDiff: validDiffs.length ? Math.max(...validDiffs) : null,
        label: "Critical",
        tone: "danger",
      };
    }
    return {
      registerHmisPercentDiff,
      hmisDhis2PercentDiff,
      registerDhis2PercentDiff,
      maxPercentDiff: validDiffs.length ? Math.max(...validDiffs) : null,
      label: "Incomplete",
      tone: "neutral",
    };
  }

  if (hasDeathOrHighRiskDifference(indicator, registerValue, hmis105Value, dhis2Value)) {
    return {
      registerHmisPercentDiff: percentDiff(registerValue, hmis105Value),
      hmisDhis2PercentDiff: percentDiff(hmis105Value, dhis2Value),
      registerDhis2PercentDiff: percentDiff(registerValue, dhis2Value),
      maxPercentDiff: null,
      label: "Critical",
      tone: "danger",
    };
  }

  if (registerValue === 0 && hmis105Value === 0 && dhis2Value === 0) {
    return {
      registerHmisPercentDiff: 0,
      hmisDhis2PercentDiff: 0,
      registerDhis2PercentDiff: 0,
      maxPercentDiff: 0,
      label: "Match",
      tone: "success",
    };
  }

  if (validDiffs.length === 0) {
    return {
      registerHmisPercentDiff,
      hmisDhis2PercentDiff,
      registerDhis2PercentDiff,
      maxPercentDiff: null,
      label: "High variance",
      tone: "danger",
    };
  }

  const maxPercentDiff = Math.max(...validDiffs);
  if (maxPercentDiff === 0) {
    return { registerHmisPercentDiff, hmisDhis2PercentDiff, registerDhis2PercentDiff, maxPercentDiff, label: "Match", tone: "success" };
  }
  if (maxPercentDiff <= DQA_GREEN_MAX_PERCENT) {
    return { registerHmisPercentDiff, hmisDhis2PercentDiff, registerDhis2PercentDiff, maxPercentDiff, label: "Within tolerance", tone: "success" };
  }
  if (maxPercentDiff <= DQA_AMBER_MAX_PERCENT) {
    return { registerHmisPercentDiff, hmisDhis2PercentDiff, registerDhis2PercentDiff, maxPercentDiff, label: "Moderate variance", tone: "warning" };
  }
  return { registerHmisPercentDiff, hmisDhis2PercentDiff, registerDhis2PercentDiff, maxPercentDiff, label: "Above tolerance", tone: "danger" };
}

export function formatPercentDiff(value: number | null) {
  return value === null ? "N/A" : `${value.toFixed(1)}%`;
}

export function DifferenceFlagBadge({ summary }: { summary: DifferenceSummary }) {
  return <Badge tone={summary.tone}>{summary.label}</Badge>;
}
