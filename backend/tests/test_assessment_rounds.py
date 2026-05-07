from app.models.facility import Facility
from app.models.indicator import Indicator


def _create_round(client, manager_token: str) -> dict:
    response = client.post(
        "/api/assessment-rounds",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "name": "March 2026 Round",
            "description": "Prompt 3 assessment round test",
            "reporting_period": "2026-03",
            "period_type": "MONTHLY",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "deadline": "2026-04-10",
            "notes": "Round fixture",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_manager_can_create_assessment_round(client, manager_token) -> None:
    payload = _create_round(client, manager_token)

    assert payload["name"] == "March 2026 Round"
    assert payload["status"] == "DRAFT"
    assert payload["reporting_period"] == "2026-03"
    assert payload["assessment_code"].startswith("UCMB-DQA-2026-03-")


def test_assessment_round_codes_are_unique_per_round(client, manager_token) -> None:
    first = _create_round(client, manager_token)
    second = _create_round(client, manager_token)

    assert first["reporting_period"] == second["reporting_period"]
    assert first["assessment_code"] != second["assessment_code"]


def test_manager_can_delete_assessment_round(client, manager_token) -> None:
    payload = _create_round(client, manager_token)

    response = client.delete(
        f"/api/assessment-rounds/{payload['id']}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    assert response.status_code == 204
    list_response = client.get("/api/assessment-rounds", headers={"Authorization": f"Bearer {manager_token}"})
    assert list_response.status_code == 200
    assert payload["id"] not in {item["id"] for item in list_response.json()}


def test_deleting_round_frees_shared_group_login_email(
    client,
    manager_token,
    active_indicator,
    active_facility,
) -> None:
    user_payload = {
        "full_name": "Assessment Group A",
        "email": "group-a@ucmb-dqa.local",
        "password": "ChangeMe123!",
        "role": "ASSESSOR",
        "is_active": True,
    }
    user_response = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {manager_token}"},
        json=user_payload,
    )
    assert user_response.status_code == 201
    shared_login_id = user_response.json()["id"]

    round_payload = _create_round(client, manager_token)
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True}]},
    )
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )
    assign_response = client.post(
        f"/api/assessment-rounds/{round_payload['id']}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": str(active_facility.id), "assessor_id": shared_login_id}]},
    )
    assert assign_response.status_code == 200

    delete_response = client.delete(
        f"/api/assessment-rounds/{round_payload['id']}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert delete_response.status_code == 204

    recreated_user_response = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {manager_token}"},
        json=user_payload,
    )
    assert recreated_user_response.status_code == 201
    assert recreated_user_response.json()["email"] == user_payload["email"]


def test_deleting_shared_group_login_frees_email(client, manager_token) -> None:
    user_payload = {
        "full_name": "Assessment Group B",
        "email": "group-b@ucmb-dqa.local",
        "password": "ChangeMe123!",
        "role": "ASSESSOR",
        "is_active": True,
    }
    user_response = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {manager_token}"},
        json=user_payload,
    )
    assert user_response.status_code == 201

    delete_response = client.delete(
        f"/api/users/{user_response.json()['id']}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert delete_response.status_code == 204

    recreated_user_response = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {manager_token}"},
        json=user_payload,
    )
    assert recreated_user_response.status_code == 201
    assert recreated_user_response.json()["email"] == user_payload["email"]


def test_manager_accounts_cannot_be_deleted(client, manager_token, seeded_manager) -> None:
    response = client.delete(
        f"/api/users/{seeded_manager.id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    assert response.status_code == 409


def test_non_manager_cannot_create_assessment_round(client, assessor_token) -> None:
    response = client.post(
        "/api/assessment-rounds",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "name": "Unauthorized Round",
            "description": None,
            "reporting_period": "2026-03",
            "period_type": "MONTHLY",
            "start_date": None,
            "end_date": None,
            "deadline": None,
            "notes": None,
        },
    )

    assert response.status_code == 403


def test_manager_can_select_indicators(client, manager_token, active_indicator) -> None:
    round_payload = _create_round(client, manager_token)

    response = client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "indicators": [
                {
                    "indicator_id": str(active_indicator.id),
                    "display_order": 1,
                    "is_required": True,
                    "custom_threshold_percent": 5,
                    "notes": "Prompt 3 indicator selection test",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["indicator_id"] == str(active_indicator.id)


def test_manager_can_create_round_from_existing_assessment_activity(client, manager_token, active_indicator) -> None:
    source_round = _create_round(client, manager_token)
    indicator_response = client.put(
        f"/api/assessment-rounds/{source_round['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "indicators": [
                {
                    "indicator_id": str(active_indicator.id),
                    "display_order": 1,
                    "is_required": True,
                    "custom_threshold_percent": 7,
                    "notes": "Copied indicator setup",
                }
            ]
        },
    )
    assert indicator_response.status_code == 200

    response = client.post(
        "/api/assessment-rounds",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "template_round_id": source_round["id"],
            "name": source_round["name"],
            "description": None,
            "reporting_period": "2026-04",
            "period_type": "MONTHLY",
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
            "deadline": "2026-05-10",
            "notes": "Second team batch under same activity",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == source_round["name"]
    assert payload["reporting_period"] == "2026-04"
    assert payload["facility_count"] == 0
    assert len(payload["selected_indicators"]) == 1
    assert payload["selected_indicators"][0]["indicator_id"] == str(active_indicator.id)
    assert payload["selected_indicators"][0]["custom_threshold_percent"] == 7.0
    assert len(payload["source_document_requirements"]) == len(source_round["source_document_requirements"])


def test_round_rejects_unmapped_indicator_selection(client, db_session, manager_token) -> None:
    indicator = Indicator(
        indicator_name="Unmapped manual indicator",
        indicator_group="Manual",
        hmis_code="MANUAL-001",
        dhis2_uid_or_operand=None,
        data_element_uid=None,
        dataset_name=None,
        hmis_section="Manual",
        source_register="Manual register",
        value_type="integer",
        is_active=True,
        is_required_by_default=True,
        default_discrepancy_threshold_percent=5.0,
        is_death_indicator=False,
        sort_order=99,
    )
    db_session.add(indicator)
    db_session.commit()
    db_session.refresh(indicator)
    round_payload = _create_round(client, manager_token)

    response = client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(indicator.id), "display_order": 1, "is_required": True}]},
    )

    assert response.status_code == 409
    assert "DHIS2 UID/operand" in response.json()["detail"]


def test_manager_can_select_facilities(client, manager_token, active_facility) -> None:
    round_payload = _create_round(client, manager_token)

    response = client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["facility_id"] == str(active_facility.id)


def test_round_rejects_facility_without_dhis2_org_unit(client, db_session, manager_token) -> None:
    facility = Facility(
        facility_name="Manual Facility",
        district="Manual District",
        facility_type="Other",
        ownership="Other",
        dhis2_org_unit_uid=None,
        is_active=True,
    )
    db_session.add(facility)
    db_session.commit()
    db_session.refresh(facility)
    round_payload = _create_round(client, manager_token)

    response = client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(facility.id)]},
    )

    assert response.status_code == 409
    assert "DHIS2 org unit UID" in response.json()["detail"]


def test_manager_can_assign_assessor_to_facility(
    client,
    manager_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    round_payload = _create_round(client, manager_token)
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True}]},
    )
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )

    response = client.post(
        f"/api/assessment-rounds/{round_payload['id']}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": str(active_facility.id), "assessor_id": str(seeded_assessor.id)}]},
    )

    assert response.status_code == 200
    assert response.json()[0]["assigned_assessor_id"] == str(seeded_assessor.id)
    assert response.json()[0]["status"] == "ASSIGNED"


def test_round_cannot_publish_with_no_indicators(client, manager_token, active_facility, seeded_assessor) -> None:
    round_payload = _create_round(client, manager_token)
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )
    client.post(
        f"/api/assessment-rounds/{round_payload['id']}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": str(active_facility.id), "assessor_id": str(seeded_assessor.id)}]},
    )

    response = client.post(
        f"/api/assessment-rounds/{round_payload['id']}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )

    assert response.status_code == 409


def test_round_cannot_publish_with_no_facilities(client, manager_token, active_indicator) -> None:
    round_payload = _create_round(client, manager_token)
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True}]},
    )

    response = client.post(
        f"/api/assessment-rounds/{round_payload['id']}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )

    assert response.status_code == 409


def test_assessor_sees_only_assigned_assessments(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    round_payload = _create_round(client, manager_token)
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True}]},
    )
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )
    client.post(
        f"/api/assessment-rounds/{round_payload['id']}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": str(active_facility.id), "assessor_id": str(seeded_assessor.id)}]},
    )
    client.post(
        f"/api/assessment-rounds/{round_payload['id']}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )

    response = client.get("/api/my-assessments", headers={"Authorization": f"Bearer {assessor_token}"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["facility_name"] == active_facility.facility_name


def test_manager_can_update_published_assessment_and_assessor_receives_changes(
    client,
    db_session,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    extra_indicator = Indicator(
        indicator_name="Published update indicator",
        indicator_group="Maternal health",
        hmis_code="HMIS-NEW",
        dhis2_uid_or_operand="newDhis2Uid123",
        data_element_uid="newDhis2Uid123",
        dataset_name="HMIS 105",
        hmis_section="Section A",
        source_register="Maternity register",
        value_type="INTEGER_ZERO_OR_POSITIVE",
        is_active=True,
        is_required_by_default=True,
        default_discrepancy_threshold_percent=5.0,
        is_death_indicator=False,
        sort_order=100,
    )
    db_session.add(extra_indicator)
    db_session.commit()
    db_session.refresh(extra_indicator)

    round_payload = _create_round(client, manager_token)
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True}]},
    )
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )
    assignment_response = client.post(
        f"/api/assessment-rounds/{round_payload['id']}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": str(active_facility.id), "assessor_id": str(seeded_assessor.id)}]},
    )
    assessment_facility_id = assignment_response.json()[0]["id"]
    publish_response = client.post(
        f"/api/assessment-rounds/{round_payload['id']}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )
    assert publish_response.status_code == 200

    update_response = client.put(
        f"/api/assessment-rounds/{round_payload['id']}",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            **round_payload,
            "name": "Updated Published Assessment",
            "source_document_requirements": [],
        },
    )
    assert update_response.status_code == 200

    indicator_update_response = client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "indicators": [
                {"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True},
                {"indicator_id": str(extra_indicator.id), "display_order": 2, "is_required": True},
            ]
        },
    )
    assert indicator_update_response.status_code == 200

    package_response = client.get(
        f"/api/my-assessments/{assessment_facility_id}",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )
    assert package_response.status_code == 200
    package = package_response.json()
    assert package["assessment_round"]["name"] == "Updated Published Assessment"
    assert {item["indicator_id"] for item in package["selected_indicators"]} == {
        str(active_indicator.id),
        str(extra_indicator.id),
    }
    assert {item["indicator_id"] for item in package["values"]} == {
        str(active_indicator.id),
        str(extra_indicator.id),
    }


def test_assessor_cannot_see_another_assessors_assignment(
    client,
    manager_token,
    assessor_two_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    round_payload = _create_round(client, manager_token)
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True}]},
    )
    facility_response = client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )
    client.post(
        f"/api/assessment-rounds/{round_payload['id']}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": str(active_facility.id), "assessor_id": str(seeded_assessor.id)}]},
    )
    client.post(
        f"/api/assessment-rounds/{round_payload['id']}/publish",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"allow_unassigned_facilities": False},
    )

    assessment_facility_id = facility_response.json()[0]["id"]
    response = client.get(
        f"/api/my-assessments/{assessment_facility_id}",
        headers={"Authorization": f"Bearer {assessor_two_token}"},
    )

    assert response.status_code == 403


def test_manager_can_view_round_progress(
    client,
    manager_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    round_payload = _create_round(client, manager_token)
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"indicators": [{"indicator_id": str(active_indicator.id), "display_order": 1, "is_required": True}]},
    )
    client.put(
        f"/api/assessment-rounds/{round_payload['id']}/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"facility_ids": [str(active_facility.id)]},
    )
    client.post(
        f"/api/assessment-rounds/{round_payload['id']}/assign",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"assignments": [{"facility_id": str(active_facility.id), "assessor_id": str(seeded_assessor.id)}]},
    )

    response = client.get(
        f"/api/assessment-rounds/{round_payload['id']}/progress",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    assert response.status_code == 200
    assert response.json()["total_facilities"] == 1
    assert response.json()["assigned_facilities"] == 1
