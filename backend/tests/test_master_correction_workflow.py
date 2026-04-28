from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.models.assessment_facility import AssessmentFacility
from app.models.base import AssessmentFacilityStatus, AssessmentTeamRole
from app.schemas.dhis2 import Dhis2ConnectionStatus
from app.schemas.facility import Dhis2FacilitySearchResult
from app.schemas.indicator import Dhis2DataElementSearchResult


def _create_round_with_scope(client, manager_token, active_facility, active_indicator):
    round_response = client.post(
        "/api/assessment-rounds",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "name": "Team Field Round",
            "description": "Team assignment test",
            "reporting_period": "2026-03",
            "period_type": "MONTHLY",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "deadline": "2026-04-10",
            "notes": None,
        },
    )
    assert round_response.status_code == 201
    round_payload = round_response.json()
    indicator_response = client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True}]},
    )
    assert indicator_response.status_code == 200
    facility_response = client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )
    assert facility_response.status_code == 200
    return round_payload, facility_response.json()[0]


def _complete_source_documents(client, token, assessment_facility_id):
    checks = [
        "ANC register",
        "Maternity register",
        "PNC register",
        "KMC register",
        "Referral register",
        "Death register",
        "HMIS 105 monthly report",
    ]
    response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/source-documents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "checks": [
                {
                    "source_document_name": name,
                    "available": True,
                    "complete": True,
                    "legible": True,
                    "missing_pages": False,
                    "comment": None,
                }
                for name in checks
            ]
        },
    )
    assert response.status_code == 200


def test_dhis2_connection_status_requires_auth_and_returns_safe_response(client, manager_token, monkeypatch):
    response = client.get("/api/dhis2/connection-status")
    assert response.status_code in {401, 403}

    monkeypatch.setattr(
        "app.routers.dhis2.check_dhis2_connection",
        lambda: Dhis2ConnectionStatus(
            connected=True,
            base_url="https://hmis.health.go.ug/api",
            last_checked_at=datetime.now(UTC),
            message="DHIS2 connection successful",
        ),
    )
    response = client.get("/api/dhis2/connection-status", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert "password" not in str(body).lower()


def test_manager_can_sign_in_and_out_of_dhis2_without_exposing_credentials(client, manager_token, monkeypatch):
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"id": "manager", "name": "DHIS2 Manager"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.auth = kwargs.get("auth")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, *args, **kwargs):
            assert self.auth == ("dhis_manager", "secret-password")
            return FakeResponse()

    monkeypatch.setattr("app.services.dhis2_service.httpx.Client", FakeClient)

    response = client.post(
        "/api/dhis2/session/login",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "base_url": "https://hmis.health.go.ug/api",
            "username": "dhis_manager",
            "password": "secret-password",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["signed_in"] is True
    assert "secret-password" not in str(body)

    status_response = client.get("/api/dhis2/connection-status", headers={"Authorization": f"Bearer {manager_token}"})
    assert status_response.status_code == 200
    assert status_response.json()["signed_in"] is True
    assert "secret-password" not in str(status_response.json())

    logout_response = client.post("/api/dhis2/session/logout", headers={"Authorization": f"Bearer {manager_token}"})
    assert logout_response.status_code == 200
    assert logout_response.json()["signed_in"] is False


def test_dhis2_search_endpoints_require_manager(client, manager_token, reviewer_token, monkeypatch):
    monkeypatch.setattr("app.routers.dhis2.search_dhis2_facilities", lambda db, query: [])
    monkeypatch.setattr("app.routers.dhis2.search_dhis2_data_elements", lambda db, query: [])

    assert client.get("/api/dhis2/facilities/search?query=pajule").status_code in {401, 403}
    assert (
        client.get(
            "/api/dhis2/facilities/search?query=pajule",
            headers={"Authorization": f"Bearer {reviewer_token}"},
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/dhis2/facilities/search?query=pajule",
            headers={"Authorization": f"Bearer {manager_token}"},
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/dhis2/data-elements/search?query=AN01",
            headers={"Authorization": f"Bearer {manager_token}"},
        ).status_code
        == 200
    )


def test_facility_import_is_idempotent(client, manager_token):
    payload = {
        "dhis2_org_unit_uid": "PajuleUid01",
        "dhis2_code": "PAJ001",
        "facility_name": "Pajule HC IV",
        "district": "Pader",
        "facility_type": "HC IV",
        "ownership": "PNFP",
        "dhis2_path": "/root/pader/pajule",
        "dhis2_parent_name": "Pader District",
        "dhis2_level": 5,
    }
    first = client.post("/api/facilities/import-from-dhis2", headers={"Authorization": f"Bearer {manager_token}"}, json=payload)
    second = client.post("/api/facilities/import-from-dhis2", headers={"Authorization": f"Bearer {manager_token}"}, json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["dhis2_code"] == "PAJ001"


def test_indicator_import_and_confirmed_seed_search_are_idempotent(client, manager_token):
    payload = {
        "indicator_name": "105-AN01a. ANC 1st Visit for women",
        "indicator_group": "ANC",
        "hmis_code": "105-AN01A",
        "dhis2_uid_or_operand": "Q9nSogNmKPt",
        "data_element_uid": "Q9nSogNmKPt",
        "category_option_combo_uid": None,
        "dataset_name": "HMIS 105:02-03 - OPD Monthly Report (MCH, FP, EID, EPI & HEPB)",
        "hmis_section": "2.1 Antenatal",
        "source_register": "ANC register",
        "category_combo": "MCH Age",
        "value_type": "INTEGER_ZERO_OR_POSITIVE",
        "aggregation_type": "SUM",
        "is_active": True,
        "is_required_by_default": True,
        "default_discrepancy_threshold_percent": 5,
        "is_death_indicator": False,
        "sort_order": 1,
        "notes": None,
    }
    first = client.post("/api/indicators/import-from-dhis2", headers={"Authorization": f"Bearer {manager_token}"}, json=payload)
    second = client.post("/api/indicators/import-from-dhis2", headers={"Authorization": f"Bearer {manager_token}"}, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    seed = client.post("/api/indicators/seed-confirmed", headers={"Authorization": f"Bearer {manager_token}"})
    assert seed.status_code == 200
    an01 = client.get("/api/indicators?search=AN01", headers={"Authorization": f"Bearer {manager_token}"})
    ma04 = client.get("/api/indicators?search=MA04", headers={"Authorization": f"Bearer {manager_token}"})
    assert any(item["hmis_code"].upper() == "105-AN01A" for item in an01.json())
    assert any(item["hmis_code"].upper() == "105-MA04" for item in ma04.json())


def test_dhis2_search_results_can_be_normalized_without_secrets(client, manager_token, monkeypatch):
    monkeypatch.setattr(
        "app.routers.dhis2.search_dhis2_facilities",
        lambda db, query: [
            Dhis2FacilitySearchResult(
                dhis2_org_unit_uid="abc123",
                dhis2_code="XYZ001",
                facility_name="Pajule HC IV",
                district="Pader",
                facility_type="HC IV",
                ownership=None,
                dhis2_path="/root/district/facility",
                dhis2_parent_name="Pader District",
                dhis2_level=5,
                already_imported=False,
            )
        ],
    )
    monkeypatch.setattr(
        "app.routers.dhis2.search_dhis2_data_elements",
        lambda db, query: [
            Dhis2DataElementSearchResult(
                data_element_uid="Q9nSogNmKPt",
                dhis2_uid_or_operand="Q9nSogNmKPt",
                name="105-AN01a. ANC 1st Visit for women",
                short_name="ANC 1st Visit",
                hmis_code="105-AN01A",
                value_type="INTEGER_ZERO_OR_POSITIVE",
                aggregation_type="SUM",
                category_combo="MCH Age",
                dataset_name="HMIS 105:02-03 - OPD Monthly Report (MCH, FP, EID, EPI & HEPB)",
                already_imported=False,
            )
        ],
    )
    facilities = client.get("/api/dhis2/facilities/search?query=pajule", headers={"Authorization": f"Bearer {manager_token}"})
    elements = client.get("/api/dhis2/data-elements/search?query=AN01", headers={"Authorization": f"Bearer {manager_token}"})
    assert facilities.status_code == 200
    assert facilities.json()[0]["facility_name"] == "Pajule HC IV"
    assert elements.status_code == 200
    assert elements.json()[0]["hmis_code"] == "105-AN01A"
    assert "password" not in str(facilities.json()).lower()


def test_team_lead_and_members_permissions(client, manager_token, active_facility, active_indicator, seeded_assessor, seeded_assessor_two, assessor_token, assessor_two_token, monkeypatch):
    monkeypatch.setattr("app.services.assessment_workspace_service.fetch_dhis2_values", lambda **_: {})
    round_payload, assignment = _create_round_with_scope(client, manager_token, active_facility, active_indicator)
    assessment_facility_id = assignment["id"]

    team_response = client.put(
        f"/api/assessment-facilities/{assessment_facility_id}/team-members",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "team_members": [
                {
                    "user_id": str(seeded_assessor.id),
                    "team_role": AssessmentTeamRole.TEAM_LEAD.value,
                    "can_enter_data": True,
                    "can_submit": True,
                },
                {
                    "user_id": str(seeded_assessor_two.id),
                    "team_role": AssessmentTeamRole.TEAM_MEMBER.value,
                    "can_enter_data": True,
                    "can_submit": False,
                },
            ]
        },
    )
    assert team_response.status_code == 200
    assert len(team_response.json()) == 2

    publish = client.post(
        f"/api/assessment-rounds/{round_payload['id']}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )
    assert publish.status_code == 200

    member_workspace = client.get(
        f"/api/my-assessments/{assessment_facility_id}/workspace",
        headers={"Authorization": f"Bearer {assessor_two_token}"},
    )
    assert member_workspace.status_code == 200
    assert member_workspace.json()["workspace_mode"] == "EDIT"

    save = client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_two_token}"},
        json={
            "values": [
                {
                    "indicator_id": str(active_indicator.id),
                    "register_value": 10,
                    "hmis105_value": 10,
                    "assessor_comment": None,
                }
            ]
        },
    )
    assert save.status_code == 200

    member_submit = client.post(
        f"/api/my-assessments/{assessment_facility_id}/submit",
        headers={"Authorization": f"Bearer {assessor_two_token}"},
    )
    assert member_submit.status_code == 403

    _complete_source_documents(client, assessor_token, assessment_facility_id)
    lead_submit = client.post(
        f"/api/my-assessments/{assessment_facility_id}/submit",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )
    assert lead_submit.status_code == 200


def test_manager_can_reassign_team_before_submission(
    client,
    db_session,
    manager_token,
    active_facility,
    active_indicator,
    seeded_assessor,
    seeded_assessor_two,
) -> None:
    round_payload, assignment = _create_round_with_scope(client, manager_token, active_facility, active_indicator)
    assessment_facility_id = assignment["id"]
    assessment_facility_uuid = UUID(assessment_facility_id)
    team_response = client.put(
        f"/api/assessment-facilities/{assessment_facility_id}/team-members",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "team_members": [
                {
                    "user_id": str(seeded_assessor.id),
                    "team_role": AssessmentTeamRole.TEAM_LEAD.value,
                    "can_enter_data": True,
                    "can_submit": True,
                }
            ]
        },
    )
    assert team_response.status_code == 200
    publish = client.post(
        f"/api/assessment-rounds/{round_payload['id']}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )
    assert publish.status_code == 200

    assessment_facility = db_session.get(AssessmentFacility, assessment_facility_uuid)
    assessment_facility.status = AssessmentFacilityStatus.IN_PROGRESS
    db_session.commit()

    reassign = client.put(
        f"/api/assessment-facilities/{assessment_facility_id}/team-members",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "team_members": [
                {
                    "user_id": str(seeded_assessor_two.id),
                    "team_role": AssessmentTeamRole.TEAM_LEAD.value,
                    "can_enter_data": True,
                    "can_submit": True,
                },
                {
                    "user_id": str(seeded_assessor.id),
                    "team_role": AssessmentTeamRole.TEAM_MEMBER.value,
                    "can_enter_data": True,
                    "can_submit": False,
                },
            ]
        },
    )

    assert reassign.status_code == 200
    assert reassign.json()[0]["user_id"] == str(seeded_assessor_two.id)
    refreshed = db_session.get(AssessmentFacility, assessment_facility_uuid)
    assert str(refreshed.assigned_assessor_id) == str(seeded_assessor_two.id)


def test_round_cannot_publish_without_team_lead(client, manager_token, active_facility, active_indicator):
    round_payload, _ = _create_round_with_scope(client, manager_token, active_facility, active_indicator)
    response = client.post(
        f"/api/assessment-rounds/{round_payload['id']}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": True},
    )
    assert response.status_code == 409
