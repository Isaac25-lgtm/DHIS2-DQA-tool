from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.models.base import AssessmentFacilityStatus
from app.models.dqa_value import DqaValue
from app.models.indicator import Indicator
from app.models.source_document_check import SourceDocumentCheck
from app.services import assessment_workspace_service
from app.services.dhis2_service import fetch_dhis2_values


def _create_published_assignment(client, manager_token: str, facility_id: str, indicator_id: str, assessor_id: str) -> str:
    round_response = client.post(
        "/api/assessment-rounds",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "name": "Prompt 4 Round",
            "description": "Workspace integration fixture",
            "reporting_period": "2026-03",
            "period_type": "MONTHLY",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "deadline": "2026-04-20",
            "notes": "Prompt 4 test",
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
    return assessment_facility_id


def test_assessor_can_open_assigned_workspace(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        assessment_workspace_service,
        "fetch_dhis2_values",
        lambda **_: {
            active_indicator.dhis2_uid_or_operand: {
                "identifier": active_indicator.dhis2_uid_or_operand,
                "value": 42,
                "status": "SUCCESS",
                "error_message": None,
                "extracted_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
            }
        },
    )
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.get(
        f"/api/my-assessments/{assessment_facility_id}/workspace",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["facility"]["facility_name"] == active_facility.facility_name
    assert len(body["selected_indicators"]) == 1
    assert body["workspace_mode"] == "EDIT"
    assert body["values"][0]["dhis2_value_at_assessment"] == 42


def test_manager_can_pre_sync_dhis2_before_publish_and_assessor_sees_value(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    calls = {"count": 0}

    def fake_fetch(**_):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                active_indicator.dhis2_uid_or_operand: {
                    "identifier": active_indicator.dhis2_uid_or_operand,
                    "value": 88,
                    "status": "SUCCESS",
                    "error_message": None,
                    "extracted_at": datetime.now(UTC),
                }
            }
        return {
            active_indicator.dhis2_uid_or_operand: {
                "identifier": active_indicator.dhis2_uid_or_operand,
                "value": None,
                "status": "ERROR",
                "error_message": "Temporary DHIS2 outage",
                "extracted_at": datetime.now(UTC),
            }
        }

    monkeypatch.setattr(assessment_workspace_service, "fetch_dhis2_values", fake_fetch)

    round_response = client.post(
        "/api/assessment-rounds",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "name": "Pre-sync Round",
            "description": "Manager pre-sync fixture",
            "reporting_period": "202603",
            "period_type": "MONTHLY",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "deadline": "2026-04-20",
            "notes": None,
        },
    )
    assert round_response.status_code == 201
    round_id = round_response.json()["id"]

    indicators_response = client.put(
        f"/api/assessment-rounds/{round_id}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True}]},
    )
    assert indicators_response.status_code == 200
    facilities_response = client.put(
        f"/api/assessment-rounds/{round_id}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )
    assert facilities_response.status_code == 200
    assessment_facility_id = facilities_response.json()[0]["id"]
    assign_response = client.post(
        f"/api/assessment-rounds/{round_id}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": str(active_facility.id), "assessor_id": str(seeded_assessor.id)}]},
    )
    assert assign_response.status_code == 200

    pre_sync = client.post(
        f"/api/assessment-rounds/{round_id}/sync-dhis2-values",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert pre_sync.status_code == 200
    assert pre_sync.json()["synced_facilities"] == 1

    publish_response = client.post(
        f"/api/assessment-rounds/{round_id}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )
    assert publish_response.status_code == 200

    workspace = client.get(
        f"/api/my-assessments/{assessment_facility_id}/workspace",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )
    assert workspace.status_code == 200
    assert workspace.json()["values"][0]["dhis2_value_at_assessment"] == 88


def test_assessor_cannot_open_another_assessors_workspace(
    client,
    manager_token,
    assessor_two_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(assessment_workspace_service, "fetch_dhis2_values", lambda **_: {})
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.get(
        f"/api/my-assessments/{assessment_facility_id}/workspace",
        headers={"Authorization": f"Bearer {assessor_two_token}"},
    )

    assert response.status_code == 403


def test_workspace_returns_selected_indicators_only(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    extra_indicator = Indicator(
        indicator_name="Not Selected",
        indicator_group="ANC",
        hmis_code="EXTRA-001",
        dhis2_uid_or_operand="ExtraUid12345",
        data_element_uid="ExtraUid12345",
        dataset_name="HMIS 105:02-03",
        hmis_section="ANC",
        source_register="ANC register",
        category_combo=None,
        value_type="integer",
        is_active=True,
        is_required_by_default=True,
        default_discrepancy_threshold_percent=5.0,
        is_death_indicator=False,
        sort_order=2,
    )
    db_session.add(extra_indicator)
    db_session.commit()
    monkeypatch.setattr(assessment_workspace_service, "fetch_dhis2_values", lambda **_: {})

    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )
    response = client.get(
        f"/api/my-assessments/{assessment_facility_id}/workspace",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )

    assert response.status_code == 200
    indicator_ids = [item["indicator_id"] for item in response.json()["selected_indicators"]]
    assert indicator_ids == [str(active_indicator.id)]
    assert str(extra_indicator.id) not in indicator_ids


def test_dhis2_service_normalizes_simple_uids_and_operands(monkeypatch) -> None:
    payload = {
        "headers": [{"name": "dx"}, {"name": "value"}],
        "rows": [
            ["idXOxt69W0e", "100"],
            ["RYcEItpNCUp.Ck8FveDhZSy", "55"],
        ],
    }

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.dhis2_service.is_dhis2_configured", lambda: True)
    monkeypatch.setattr(
        "app.services.dhis2_service.get_settings",
        lambda: SimpleNamespace(
            dhis2_base_url="https://example.org/api",
            dhis2_username="demo",
            dhis2_password="demo",
        ),
    )
    monkeypatch.setattr("app.services.dhis2_service.httpx.Client", FakeClient)

    response = fetch_dhis2_values(
        facility_uid="facility123",
        reporting_period="2026-03",
        period_type="MONTHLY",
        identifiers=["idXOxt69W0e", "RYcEItpNCUp.Ck8FveDhZSy"],
    )

    assert response["idXOxt69W0e"]["value"] == 100
    assert response["idXOxt69W0e"]["status"] == "SUCCESS"
    assert response["RYcEItpNCUp.Ck8FveDhZSy"]["value"] == 55


def test_dhis2_failure_does_not_prevent_workspace_loading(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        assessment_workspace_service,
        "fetch_dhis2_values",
        lambda **_: {
            active_indicator.dhis2_uid_or_operand: {
                "identifier": active_indicator.dhis2_uid_or_operand,
                "value": None,
                "status": "ERROR",
                "error_message": "DHIS2 timeout",
                "extracted_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
            }
        },
    )
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.get(
        f"/api/my-assessments/{assessment_facility_id}/workspace",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )

    assert response.status_code == 200
    assert response.json()["dhis2_pull_message"] is not None
    assert len(response.json()["selected_indicators"]) == 1


def test_assessor_can_retry_dhis2_pull(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        assessment_workspace_service,
        "fetch_dhis2_values",
        lambda **_: {
            active_indicator.dhis2_uid_or_operand: {
                "identifier": active_indicator.dhis2_uid_or_operand,
                "value": 56,
                "status": "SUCCESS",
                "error_message": None,
                "extracted_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
            }
        },
    )
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/pull-dhis2",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["values"][0]["value"] == 56
    assert body["values"][0]["status"] == "SUCCESS"


def test_assessor_can_save_draft_values_online(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 100,
                    "hmis105_value": 98,
                    "assessor_comment": "Draft saved online",
                }
            ]
        },
    )

    assert response.status_code == 200
    saved_value = db_session.query(DqaValue).filter_by(assessment_facility_id=assessment_facility_id).one()
    assert saved_value.register_value == 100
    assert saved_value.hmis105_value == 98


def test_assessor_can_save_source_document_checks(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/source-documents",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "checks": [
                {
                    "source_document_name": "ANC register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "Present and clean",
                }
            ]
        },
    )

    assert response.status_code == 200
    saved_check = db_session.query(SourceDocumentCheck).filter_by(assessment_facility_id=assessment_facility_id).one()
    assert saved_check.available is True
    assert saved_check.legible is True


def test_assessor_can_save_general_facility_comment(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/general-comment",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={"general_assessment_comment": "HMIS 105 report was verified with the records officer."},
    )

    assert response.status_code == 200
    assert response.json()["general_assessment_comment"] == "HMIS 105 report was verified with the records officer."
    db_session.expire_all()
    workspace_response = client.get(
        f"/api/my-assessments/{assessment_facility_id}/workspace",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )
    assert workspace_response.status_code == 200
    assert (
        workspace_response.json()["assessment_facility"]["general_assessment_comment"]
        == "HMIS 105 report was verified with the records officer."
    )


def test_manager_can_view_workspace_read_only(
    client,
    manager_token,
    reviewer_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(assessment_workspace_service, "fetch_dhis2_values", lambda **_: {})
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.get(
        f"/api/assessment-facilities/{assessment_facility_id}/workspace",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    assert response.status_code == 200
    assert response.json()["workspace_mode"] == "READ_ONLY"


def test_submit_assessment_does_not_require_source_document_checklist(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )
    save_response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 100,
                    "hmis105_value": 98,
                    "assessor_comment": "",
                }
            ]
        },
    )
    assert save_response.status_code == 200

    response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/submit",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )

    assert response.status_code == 200
    db_session.expire_all()
    saved_value = db_session.query(DqaValue).filter_by(assessment_facility_id=assessment_facility_id).one()
    assert saved_value.assessment_facility.status == AssessmentFacilityStatus.SUBMITTED


def test_submit_assessment_updates_status(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )
    client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 100,
                    "hmis105_value": 98,
                    "assessor_comment": "",
                }
            ]
        },
    )
    client.post(
        f"/api/my-assessments/{assessment_facility_id}/source-documents",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "checks": [
                {
                    "source_document_name": "ANC register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "Maternity register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "PNC register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "KMC register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "Referral register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "Death register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "HMIS 105 monthly report",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
            ]
        },
    )

    response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/submit",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )

    assert response.status_code == 200
    db_session.expire_all()
    saved_status = db_session.query(DqaValue).filter_by(assessment_facility_id=assessment_facility_id).one()
    assert saved_status.assessment_facility.status == AssessmentFacilityStatus.SUBMITTED


def test_submitted_assessments_cannot_be_edited(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    assessment_facility_id = _create_published_assignment(
        client,
        manager_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )
    client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 100,
                    "hmis105_value": 98,
                    "assessor_comment": "",
                }
            ]
        },
    )
    client.post(
        f"/api/my-assessments/{assessment_facility_id}/source-documents",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "checks": [
                {
                    "source_document_name": "ANC register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "Maternity register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "PNC register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "KMC register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "Referral register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "Death register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
                {
                    "source_document_name": "HMIS 105 monthly report",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "",
                },
            ]
        },
    )
    client.post(
        f"/api/my-assessments/{assessment_facility_id}/submit",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )

    response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 101,
                    "hmis105_value": 99,
                    "assessor_comment": "Should fail",
                }
            ]
        },
    )

    assert response.status_code == 409
