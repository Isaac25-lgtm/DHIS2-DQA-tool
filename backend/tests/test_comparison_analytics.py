from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.models.base import ComparisonStatus, DqaIssueType, SeverityLevel
from app.models.dqa_value import DqaValue
from app.models.indicator import Indicator
from app.services.comparison_service import compare_single_value
from app.services.scoring_service import calculate_facility_score


def _create_published_assignment(client, manager_token: str, facility_id: str, indicator_id: str, assessor_id: str) -> tuple[str, str]:
    round_response = client.post(
        "/api/assessment-rounds",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "name": "Prompt 5 Round",
            "description": "Comparison fixture",
            "reporting_period": "2026-03",
            "period_type": "MONTHLY",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "deadline": "2026-04-20",
            "notes": "Prompt 5 comparison test",
        },
    )
    assert round_response.status_code == 201
    round_id = round_response.json()["id"]

    indicators_response = client.put(
        f"/api/assessment-rounds/{round_id}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": indicator_id, "display_order": 1, "is_required": True}]},
    )
    assert indicators_response.status_code == 200

    facilities_response = client.put(
        f"/api/assessment-rounds/{round_id}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [facility_id]},
    )
    assert facilities_response.status_code == 200
    assessment_facility_id = facilities_response.json()[0]["id"]

    assign_response = client.post(
        f"/api/assessment-rounds/{round_id}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": facility_id, "assessor_id": assessor_id}]},
    )
    assert assign_response.status_code == 200

    publish_response = client.post(
        f"/api/assessment-rounds/{round_id}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )
    assert publish_response.status_code == 200
    return round_id, assessment_facility_id


def _selected_indicator(hmis_code: str = "FIX-ROUND-001", is_death_indicator: bool = False, threshold: float = 5.0):
    indicator = SimpleNamespace(
        indicator_name="Fixture Indicator",
        hmis_code=hmis_code,
        is_death_indicator=is_death_indicator,
        default_discrepancy_threshold_percent=threshold,
    )
    return SimpleNamespace(
        indicator=indicator,
        custom_threshold_percent=None,
        indicator_id=uuid4(),
        display_order=1,
        is_required=True,
    )


def _dqa_value(register_value, hmis105_value, dhis2_value):
    return DqaValue(
        assessment_facility_id=uuid4(),
        indicator_id=uuid4(),
        register_value=register_value,
        hmis105_value=hmis105_value,
        dhis2_value_at_assessment=dhis2_value,
    )


def test_comparison_exact_match_returns_no_issue_and_exact() -> None:
    value = _dqa_value(100, 100, 100)
    compared = compare_single_value(value, _selected_indicator(), None)
    assert compared.issue_type == DqaIssueType.NO_ISSUE
    assert compared.severity == SeverityLevel.EXACT
    assert compared.comparison_status == ComparisonStatus.COMPARED


def test_register_to_hmis_mismatch_with_hmis_matching_dhis2_returns_summarization_error() -> None:
    value = _dqa_value(100, 105, 105)
    compared = compare_single_value(value, _selected_indicator(), None)
    assert compared.issue_type == DqaIssueType.REGISTER_TO_HMIS_SUMMARIZATION_ERROR


def test_register_hmis_match_but_dhis2_differs_returns_dhis2_data_entry_error() -> None:
    value = _dqa_value(100, 100, 90)
    compared = compare_single_value(value, _selected_indicator(), None)
    assert compared.issue_type == DqaIssueType.DHIS2_DATA_ENTRY_ERROR


def test_all_three_differ_returns_multiple_stage_error() -> None:
    value = _dqa_value(100, 90, 95)
    compared = compare_single_value(value, _selected_indicator(), None)
    assert compared.issue_type == DqaIssueType.MULTIPLE_STAGE_ERROR


def test_null_register_returns_source_document_issue_or_value_missing() -> None:
    value = _dqa_value(None, 50, 50)
    compared = compare_single_value(value, _selected_indicator(), None)
    assert compared.issue_type == DqaIssueType.SOURCE_DOCUMENT_ISSUE
    assert compared.severity == SeverityLevel.MISSING


def test_null_dhis2_returns_dhis2_value_missing() -> None:
    value = _dqa_value(50, 50, None)
    compared = compare_single_value(value, _selected_indicator(), None)
    assert compared.issue_type == DqaIssueType.DHIS2_VALUE_MISSING
    assert compared.severity == SeverityLevel.MISSING


def test_register_zero_and_dhis2_zero_does_not_divide_by_zero() -> None:
    value = _dqa_value(0, 0, 0)
    value.dhis2_api_status = "SUCCESS"
    compared = compare_single_value(value, _selected_indicator(), None)
    assert compared.issue_type == DqaIssueType.NO_ISSUE
    assert compared.severity == SeverityLevel.EXACT
    assert float(compared.discrepancy_percent) == 0.0


def test_register_hmis_zero_and_dhis2_no_data_is_not_exact() -> None:
    value = _dqa_value(0, 0, 0)
    value.dhis2_api_status = "NO_DATA"
    compared = compare_single_value(value, _selected_indicator(), None)
    assert compared.issue_type == DqaIssueType.DHIS2_VALUE_MISSING
    assert compared.severity == SeverityLevel.MISSING
    assert compared.comparison_status == ComparisonStatus.NEEDS_REVIEW
    assert "must not be interpreted as true zero" in compared.comparison_notes


def test_register_zero_and_dhis2_positive_sets_major_or_critical_without_percent() -> None:
    value = _dqa_value(0, 0, 5)
    compared = compare_single_value(value, _selected_indicator(), None)
    assert compared.discrepancy_percent is None
    assert compared.severity in {SeverityLevel.MAJOR, SeverityLevel.CRITICAL}


def test_death_indicator_difference_of_one_is_critical() -> None:
    value = _dqa_value(1, 1, 2)
    compared = compare_single_value(value, _selected_indicator(hmis_code="105-MA13", is_death_indicator=True), None)
    assert compared.severity == SeverityLevel.CRITICAL


def test_dqa_score_calculation_works() -> None:
    indicator_id_1 = uuid4()
    indicator_id_2 = uuid4()
    exact_value = DqaValue(indicator_id=indicator_id_1, assessment_facility_id=uuid4(), severity=SeverityLevel.EXACT)
    moderate_value = DqaValue(indicator_id=indicator_id_2, assessment_facility_id=uuid4(), severity=SeverityLevel.MODERATE)
    score = calculate_facility_score([exact_value, moderate_value], {indicator_id_1, indicator_id_2}, None)
    assert score["score_percent"] == 75.0
    assert score["score_category"] == "GOOD"


def test_manager_can_run_comparison(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    _, assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    save_response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={"values": [{"indicator_id": str(active_indicator.id), "register_value": 100, "hmis105_value": 100}]},
    )
    assert save_response.status_code == 200

    response = client.post(
        f"/api/assessment-facilities/{assessment_facility_id}/run-comparison",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    assert response.status_code == 200
    assert response.json()["compared_rows"] == 1


def test_assessor_cannot_run_comparison_for_unassigned_assessment(
    client,
    manager_token,
    assessor_two_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    _, assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    response = client.post(
        f"/api/assessment-facilities/{assessment_facility_id}/run-comparison",
        headers={"Authorization": f"Bearer {assessor_two_token}"},
    )
    assert response.status_code == 403


def test_analytics_summary_returns_expected_counts(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    round_id, assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={"values": [{"indicator_id": str(active_indicator.id), "register_value": 80, "hmis105_value": 80}]},
    )
    saved_value = (
        db_session.query(DqaValue)
        .filter_by(assessment_facility_id=UUID(assessment_facility_id), indicator_id=active_indicator.id)
        .one()
    )
    saved_value.dhis2_value_at_assessment = 80
    db_session.commit()
    client.post(
        f"/api/assessment-facilities/{assessment_facility_id}/run-comparison",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    response = client.get(
        f"/api/analytics/assessment-rounds/{round_id}/summary",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["indicators_assessed"] == 1
    assert body["exact_match_rate"] == 100.0


def test_heatmap_returns_facility_indicator_cells(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    round_id, assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={"values": [{"indicator_id": str(active_indicator.id), "register_value": 75, "hmis105_value": 75}]},
    )
    saved_value = (
        db_session.query(DqaValue)
        .filter_by(assessment_facility_id=UUID(assessment_facility_id), indicator_id=active_indicator.id)
        .one()
    )
    saved_value.dhis2_value_at_assessment = 75
    db_session.commit()
    client.post(
        f"/api/assessment-facilities/{assessment_facility_id}/run-comparison",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    response = client.get(
        f"/api/analytics/assessment-rounds/{round_id}/heatmap",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["facility_id"] == str(active_facility.id)
    assert body[0]["indicator_id"] == str(active_indicator.id)


def test_corrective_action_can_be_created(
    client,
    manager_token,
    active_facility,
    active_indicator,
) -> None:
    response = client.post(
        "/api/corrective-actions",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "facility_id": str(active_facility.id),
            "indicator_id": str(active_indicator.id),
            "issue_type": "DHIS2_DATA_ENTRY_ERROR",
            "severity": "MAJOR",
            "action_description": "Verify DHIS2 entry against the approved HMIS 105 report.",
            "recommended_action": "Check the reporting chain.",
            "deadline": str(date.today() + timedelta(days=7)),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "OPEN"


def test_corrective_action_status_flow_works(
    client,
    manager_token,
    reviewer_token,
    active_facility,
    active_indicator,
) -> None:
    create_response = client.post(
        "/api/corrective-actions",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "facility_id": str(active_facility.id),
            "indicator_id": str(active_indicator.id),
            "issue_type": "MULTIPLE_STAGE_ERROR",
            "severity": "CRITICAL",
            "action_description": "Trace the full reporting chain.",
            "deadline": str(date.today() + timedelta(days=3)),
        },
    )
    action_id = create_response.json()["id"]

    status_response = client.patch(
        f"/api/corrective-actions/{action_id}/status",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"status": "IN_PROGRESS"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "IN_PROGRESS"

    resolve_response = client.post(
        f"/api/corrective-actions/{action_id}/resolve",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"resolution_comment": "Facility team completed recount and updated report."},
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "RESOLVED"

    verify_response = client.post(
        f"/api/corrective-actions/{action_id}/verify",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"verification_comment": "Verified during follow-up review."},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "VERIFIED"

    close_response = client.post(
        f"/api/corrective-actions/{action_id}/close",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"manager_comment": "Closed after verification."},
    )
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "CLOSED"


def test_corrective_action_overdue_detection_works(
    client,
    manager_token,
    active_facility,
    active_indicator,
) -> None:
    client.post(
        "/api/corrective-actions",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "facility_id": str(active_facility.id),
            "indicator_id": str(active_indicator.id),
            "issue_type": "SOURCE_DOCUMENT_ISSUE",
            "severity": "MAJOR",
            "action_description": "Locate missing source document pages.",
            "deadline": str(date.today() - timedelta(days=1)),
        },
    )

    response = client.get(
        "/api/corrective-actions",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["status"] == "OVERDUE"
