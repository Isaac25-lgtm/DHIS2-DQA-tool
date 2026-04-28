from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from app.models.ai_generation_log import AiGenerationLog
from app.models.dqa_value import DqaValue
from app.models.export_log import ExportLog
from app.models.report import Report


def _create_published_assignment(client, manager_token: str, facility_id: str, indicator_id: str, assessor_id: str) -> tuple[str, str]:
    round_response = client.post(
        "/api/assessment-rounds",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "name": "Prompt 6 Round",
            "description": "Report fixture",
            "reporting_period": "2026-03",
            "period_type": "MONTHLY",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "deadline": "2026-04-20",
            "notes": "Prompt 6 reporting test",
        },
    )
    assert round_response.status_code == 201
    round_id = round_response.json()["id"]

    client.put(
        f"/api/assessment-rounds/{round_id}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": indicator_id, "display_order": 1, "is_required": True}]},
    )
    facilities_response = client.put(
        f"/api/assessment-rounds/{round_id}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [facility_id]},
    )
    assessment_facility_id = facilities_response.json()[0]["id"]
    client.post(
        f"/api/assessment-rounds/{round_id}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": facility_id, "assessor_id": assessor_id}]},
    )
    client.post(
        f"/api/assessment-rounds/{round_id}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )
    return round_id, assessment_facility_id


def _prepare_compared_assessment(
    client,
    db_session,
    manager_token: str,
    assessor_token: str,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> tuple[str, str]:
    round_id, assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 100,
                    "hmis105_value": 95,
                    "assessor_comment": "Assessor note should be optional in reports.",
                }
            ]
        },
    )
    saved_value = (
        db_session.query(DqaValue)
        .filter_by(assessment_facility_id=UUID(assessment_facility_id), indicator_id=active_indicator.id)
        .one()
    )
    saved_value.dhis2_value_at_assessment = 95
    db_session.commit()

    client.post(
        f"/api/assessment-facilities/{assessment_facility_id}/run-comparison",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    return round_id, assessment_facility_id


def test_manager_can_generate_facility_report(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "assessment_facility_id": assessment_facility_id,
            "report_type": "FACILITY_DQA_REPORT",
            "include_comments": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["report_type"] == "FACILITY_DQA_REPORT"


def test_manager_can_generate_consolidated_report(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    round_id, _ = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "assessment_round_id": round_id,
            "report_type": "CONSOLIDATED_UCMB_DQA_REPORT",
            "include_comments": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["report_type"] == "CONSOLIDATED_UCMB_DQA_REPORT"


def test_report_generation_uses_template_fallback_without_ai_api_key(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False},
    )
    assert response.status_code == 200
    assert "Overall Data Quality Summary" in response.json()["generated_content"]


def test_ai_payload_excludes_comments_by_default(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False},
    )
    assert response.status_code == 200
    row = response.json()["structured_input_json"]["comparison_rows"][0]
    assert "assessor_comment" not in row


def test_include_comments_true_includes_comments_only_when_requested(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": True},
    )
    assert response.status_code == 200
    row = response.json()["structured_input_json"]["comparison_rows"][0]
    assert row["assessor_comment"] == "Assessor note should be optional in reports."


def test_report_saved_as_generated_not_approved(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "GENERATED"


def test_manager_can_edit_review_and_approve_report(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    generate_response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False},
    )
    report_id = generate_response.json()["id"]

    edit_response = client.put(
        f"/api/reports/{report_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"edited_content": "Edited report body."},
    )
    assert edit_response.status_code == 200
    assert edit_response.json()["edited_content"] == "Edited report body."

    review_response = client.post(f"/api/reports/{report_id}/review", headers={"Authorization": f"Bearer {manager_token}"})
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "REVIEWED"

    approve_response = client.post(f"/api/reports/{report_id}/approve", headers={"Authorization": f"Bearer {manager_token}"})
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"


def test_viewer_and_assessor_cannot_generate_official_reports(
    client,
    db_session,
    viewer_token,
    assessor_token,
    manager_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    payload = {"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False}
    viewer_response = client.post("/api/reports/generate", headers={"Authorization": f"Bearer {viewer_token}"}, json=payload)
    assessor_response = client.post("/api/reports/generate", headers={"Authorization": f"Bearer {assessor_token}"}, json=payload)
    assert viewer_response.status_code == 403
    assert assessor_response.status_code == 403


def test_docx_and_xlsx_export_return_file_responses_and_logs_are_saved(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    generate_response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False},
    )
    report_id = generate_response.json()["id"]
    client.post(f"/api/reports/{report_id}/approve", headers={"Authorization": f"Bearer {manager_token}"})

    docx_response = client.get(f"/api/reports/{report_id}/export/docx", headers={"Authorization": f"Bearer {manager_token}"})
    xlsx_response = client.get(f"/api/reports/{report_id}/export/xlsx", headers={"Authorization": f"Bearer {manager_token}"})

    assert docx_response.status_code == 200
    assert "attachment" in docx_response.headers["content-disposition"]
    assert xlsx_response.status_code == 200
    assert db_session.query(ExportLog).filter_by(report_id=UUID(report_id)).count() >= 2


def test_pdf_export_handles_dependency_availability_gracefully(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    generate_response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False},
    )
    report_id = generate_response.json()["id"]
    client.post(f"/api/reports/{report_id}/approve", headers={"Authorization": f"Bearer {manager_token}"})
    response = client.get(f"/api/reports/{report_id}/export/pdf", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code in {200, 503}
    if response.status_code == 503:
        assert "PDF export dependency" in response.json()["detail"]


def test_export_requires_authentication(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    generate_response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False},
    )
    report_id = generate_response.json()["id"]
    client.post(f"/api/reports/{report_id}/approve", headers={"Authorization": f"Bearer {manager_token}"})
    response = client.get(f"/api/reports/{report_id}/export/docx")
    assert response.status_code == 401


def test_report_access_respects_permissions(
    client,
    db_session,
    manager_token,
    assessor_token,
    assessor_two_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    generate_response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False},
    )
    report_id = generate_response.json()["id"]
    allowed = client.get(f"/api/reports/{report_id}", headers={"Authorization": f"Bearer {assessor_token}"})
    denied = client.get(f"/api/reports/{report_id}", headers={"Authorization": f"Bearer {assessor_two_token}"})
    assert allowed.status_code == 200
    assert denied.status_code == 403


def test_ai_generation_log_is_saved(
    client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
) -> None:
    _, assessment_facility_id = _prepare_compared_assessment(
        client, db_session, manager_token, assessor_token, active_facility, active_indicator, seeded_assessor
    )
    response = client.post(
        "/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assessment_facility_id": assessment_facility_id, "report_type": "FACILITY_DQA_REPORT", "include_comments": False},
    )
    assert response.status_code == 200
    report_id = UUID(response.json()["id"])
    assert db_session.query(AiGenerationLog).filter_by(report_id=report_id).count() == 1
