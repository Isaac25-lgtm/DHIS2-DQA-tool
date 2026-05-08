from __future__ import annotations

from app.models.base import AssessmentFacilityStatus
from app.models.dqa_value import DqaValue
from app.models.source_document_check import SourceDocumentCheck
from app.models.sync_log import SyncLog
from app.services import assessment_workspace_service

from .test_assessment_workspace import _create_published_assignment


def _seed_required_docs(client, assessment_facility_id: str, assessor_token: str) -> None:
    response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/source-documents",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "checks": [
                {"source_document_name": "ANC register", "available": True, "complete": True, "legible": True, "missing_pages": False, "comment": ""},
                {"source_document_name": "Maternity register", "available": True, "complete": True, "legible": True, "missing_pages": False, "comment": ""},
                {"source_document_name": "PNC register", "available": True, "complete": True, "legible": True, "missing_pages": False, "comment": ""},
                {"source_document_name": "KMC register", "available": True, "complete": True, "legible": True, "missing_pages": False, "comment": ""},
                {"source_document_name": "Referral register", "available": True, "complete": True, "legible": True, "missing_pages": False, "comment": ""},
                {"source_document_name": "Death register", "available": True, "complete": True, "legible": True, "missing_pages": False, "comment": ""},
                {"source_document_name": "HMIS 105 monthly report", "available": True, "complete": True, "legible": True, "missing_pages": False, "comment": ""},
            ]
        },
    )
    assert response.status_code == 200


def test_sync_requires_authentication(client) -> None:
    response = client.post(
        "/api/sync/assessment-draft",
        json={
            "assessment_facility_id": "00000000-0000-0000-0000-000000000001",
            "client_batch_id": "batch-1",
            "client_saved_at": "2026-04-26T12:00:00Z",
            "values": [],
            "source_document_checks": [],
            "submit_final": False,
        },
    )
    assert response.status_code == 401


def test_assessor_can_sync_assigned_assessment(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(assessment_workspace_service, "fetch_dhis2_values", lambda **_: {})
    assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    response = client.post(
        "/api/sync/assessment-draft",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "assessment_facility_id": assessment_facility_id,
            "client_batch_id": "sync-batch-1",
            "client_saved_at": "2026-04-26T12:00:00Z",
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 100,
                    "hmis105_value": 98,
                    "assessor_comment": "offline draft",
                    "local_client_id": "local-1",
                }
            ],
            "source_document_checks": [],
            "submit_final": False,
        },
    )
    assert response.status_code == 200
    value = db_session.query(DqaValue).filter_by(assessment_facility_id=assessment_facility_id).one()
    assert value.register_value == 100
    assert value.hmis105_value == 98


def test_assessor_cannot_sync_another_assessors_assessment(
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
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    response = client.post(
        "/api/sync/assessment-draft",
        headers={"Authorization": f"Bearer {assessor_two_token}"},
        json={
            "assessment_facility_id": assessment_facility_id,
            "client_batch_id": "sync-batch-2",
            "client_saved_at": "2026-04-26T12:00:00Z",
            "values": [],
            "source_document_checks": [],
            "submit_final": False,
        },
    )
    assert response.status_code in {403, 409}


def test_sync_upserts_without_duplicates_and_preserves_dhis2(
    client,
    db_session,
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
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    client.get(
        f"/api/my-assessments/{assessment_facility_id}/workspace",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )

    payload = {
        "assessment_facility_id": assessment_facility_id,
        "client_batch_id": "sync-batch-3",
        "client_saved_at": "2026-04-26T12:00:00Z",
        "values": [
            {
                "indicator_id": str(active_indicator.id),
                "register_value": 101,
                "hmis105_value": 99,
                "assessor_comment": "sync value",
                "local_client_id": "local-3",
            }
        ],
        "source_document_checks": [],
        "submit_final": False,
    }

    first = client.post("/api/sync/assessment-draft", headers={"Authorization": f"Bearer {assessor_token}"}, json=payload)
    second = client.post("/api/sync/assessment-draft", headers={"Authorization": f"Bearer {assessor_token}"}, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate_batch"] is True
    values = db_session.query(DqaValue).filter_by(assessment_facility_id=assessment_facility_id).all()
    assert len(values) == 1
    assert values[0].dhis2_value_at_assessment == 42


def test_sync_saves_source_document_checks(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(assessment_workspace_service, "fetch_dhis2_values", lambda **_: {})
    assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    response = client.post(
        "/api/sync/assessment-draft",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "assessment_facility_id": assessment_facility_id,
            "client_batch_id": "sync-batch-4",
            "client_saved_at": "2026-04-26T12:00:00Z",
            "values": [],
            "source_document_checks": [
                {
                    "source_document_name": "ANC register",
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": "ok",
                }
            ],
            "submit_final": False,
        },
    )
    assert response.status_code == 200
    check = db_session.query(SourceDocumentCheck).filter_by(assessment_facility_id=assessment_facility_id).one()
    assert check.available is True


def test_submit_final_through_sync_submits_assessment(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(assessment_workspace_service, "fetch_dhis2_values", lambda **_: {})
    assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    _seed_required_docs(client, assessment_facility_id, assessor_token)
    response = client.post(
        "/api/sync/assessment-draft",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "assessment_facility_id": assessment_facility_id,
            "client_batch_id": "sync-batch-5",
            "client_saved_at": "2026-04-26T12:00:00Z",
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 105,
                    "hmis105_value": 104,
                    "assessor_comment": "",
                    "local_client_id": "local-5",
                }
            ],
            "source_document_checks": [],
            "submit_final": True,
        },
    )
    assert response.status_code == 200
    value = db_session.query(DqaValue).filter_by(assessment_facility_id=assessment_facility_id).one()
    assert value.assessment_facility.status == AssessmentFacilityStatus.SUBMITTED


def test_submit_final_through_sync_fails_cleanly_if_required_values_missing(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(assessment_workspace_service, "fetch_dhis2_values", lambda **_: {})
    assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    _seed_required_docs(client, assessment_facility_id, assessor_token)
    response = client.post(
        "/api/sync/assessment-draft",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "assessment_facility_id": assessment_facility_id,
            "client_batch_id": "sync-batch-6",
            "client_saved_at": "2026-04-26T12:00:00Z",
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": None,
                    "hmis105_value": None,
                    "assessor_comment": "",
                    "local_client_id": "local-6",
                }
            ],
            "source_document_checks": [],
            "submit_final": True,
        },
    )
    assert response.status_code == 409


def test_submitted_assessment_can_be_synced_again(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    monkeypatch,
) -> None:
    monkeypatch.setattr(assessment_workspace_service, "fetch_dhis2_values", lambda **_: {})
    assessment_facility_id = _create_published_assignment(
        client, manager_token, str(active_facility.id), str(active_indicator.id), str(seeded_assessor.id)
    )
    _seed_required_docs(client, assessment_facility_id, assessor_token)
    submit_response = client.post(
        "/api/sync/assessment-draft",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "assessment_facility_id": assessment_facility_id,
            "client_batch_id": "sync-batch-7",
            "client_saved_at": "2026-04-26T12:00:00Z",
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 100,
                    "hmis105_value": 100,
                    "assessor_comment": "",
                    "local_client_id": "local-7",
                }
            ],
            "source_document_checks": [],
            "submit_final": True,
        },
    )
    assert submit_response.status_code == 200

    second_response = client.post(
        "/api/sync/assessment-draft",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "assessment_facility_id": assessment_facility_id,
            "client_batch_id": "sync-batch-8",
            "client_saved_at": "2026-04-26T12:01:00Z",
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 101,
                    "hmis105_value": 101,
                    "assessor_comment": "",
                    "local_client_id": "local-8",
                }
            ],
            "source_document_checks": [],
            "submit_final": False,
        },
    )
    assert second_response.status_code == 200
    db_session.expire_all()
    value = db_session.query(DqaValue).filter_by(assessment_facility_id=assessment_facility_id).one()
    assert value.register_value == 101
    assert value.hmis105_value == 101
    assert value.assessment_facility.status == AssessmentFacilityStatus.SUBMITTED
    assert db_session.query(SyncLog).filter_by(assessment_facility_id=assessment_facility_id).count() >= 1
