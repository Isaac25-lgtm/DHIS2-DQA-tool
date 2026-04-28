from __future__ import annotations

from collections import Counter

from app.models.base import SeverityLevel
from app.models.dqa_value import DqaValue

DEFAULT_SCORING_WEIGHTS = {
    SeverityLevel.EXACT.value: 1.0,
    SeverityLevel.MINOR.value: 0.75,
    SeverityLevel.MODERATE.value: 0.5,
    SeverityLevel.MAJOR.value: 0.0,
    SeverityLevel.CRITICAL.value: 0.0,
    SeverityLevel.MISSING.value: 0.0,
    SeverityLevel.NOT_APPLICABLE.value: None,
}


def get_scoring_weights(scoring_settings_json: dict | None) -> dict[str, float | None]:
    weights = DEFAULT_SCORING_WEIGHTS.copy()
    configured = (scoring_settings_json or {}).get("weights") if isinstance(scoring_settings_json, dict) else None
    if isinstance(configured, dict):
        for key, value in configured.items():
            if key in weights:
                weights[key] = value
    return weights


def categorize_score(score_percent: float) -> str:
    if score_percent >= 90:
        return "EXCELLENT"
    if score_percent >= 75:
        return "GOOD"
    if score_percent >= 60:
        return "NEEDS_IMPROVEMENT"
    return "POOR"


def calculate_facility_score(
    values: list[DqaValue],
    required_indicator_ids: set,
    scoring_settings_json: dict | None,
) -> dict[str, float | int | str]:
    weights = get_scoring_weights(scoring_settings_json)
    counter: Counter[str] = Counter()
    earned_points = 0.0
    possible_points = 0.0

    for value in values:
        if value.indicator_id not in required_indicator_ids:
            continue
        severity = value.severity.value if value.severity else SeverityLevel.NOT_APPLICABLE.value
        counter[severity] += 1
        weight = weights.get(severity)
        if weight is None:
            continue
        possible_points += 1.0
        earned_points += float(weight)

    score_percent = round((earned_points / possible_points) * 100, 2) if possible_points else 0.0
    return {
        "score_percent": score_percent,
        "score_category": categorize_score(score_percent),
        "earned_points": round(earned_points, 2),
        "possible_points": round(possible_points, 2),
        "exact_count": counter[SeverityLevel.EXACT.value],
        "minor_count": counter[SeverityLevel.MINOR.value],
        "moderate_count": counter[SeverityLevel.MODERATE.value],
        "major_count": counter[SeverityLevel.MAJOR.value],
        "critical_count": counter[SeverityLevel.CRITICAL.value],
        "missing_count": counter[SeverityLevel.MISSING.value],
        "not_applicable_count": counter[SeverityLevel.NOT_APPLICABLE.value],
    }
