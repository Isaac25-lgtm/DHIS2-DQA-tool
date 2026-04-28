from __future__ import annotations


def _create_submission(client, manager_token: str, assessor_token: str, facility_id: str, indicator_id: str, assessor_id: str) -> str:
    round_response = client.post(
        "/api/assessment-rounds",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "name": "Submission Round",
            "description": "Submitted data fixture",
            "reporting_period": "2026-03",
            "period_type": "MONTHLY",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "deadline": "2026-04-20",
            "notes": "Submission test",
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

    save_response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/values",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "values": [
                {
                    "indicator_id": indicator_id,
                    "register_value": 100,
                    "hmis105_value": 92,
                    "assessor_comment": "",
                }
            ]
        },
    )
    assert save_response.status_code == 200

    submit_response = client.post(
        f"/api/my-assessments/{assessment_facility_id}/send-to-manager",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )
    assert submit_response.status_code == 200
    return assessment_facility_id


def test_manager_can_view_submitted_data_and_cumulative_stats(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    assessment_facility_id = _create_submission(
        client,
        manager_token,
        assessor_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.get("/api/submissions", headers={"Authorization": f"Bearer {manager_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["submitted_facilities"] == 1
    assert body["stats"]["total_submitted_rows"] == 1
    assert body["submissions"][0]["assessment_facility_id"] == assessment_facility_id
    assert body["submissions"][0]["flagged_rows"] >= 0


def test_manager_can_download_submissions_excel(
    client,
    manager_token,
    assessor_token,
    active_facility,
    active_indicator,
    seeded_assessor,
) -> None:
    _create_submission(
        client,
        manager_token,
        assessor_token,
        str(active_facility.id),
        str(active_indicator.id),
        str(seeded_assessor.id),
    )

    response = client.get("/api/submissions/export/xlsx", headers={"Authorization": f"Bearer {manager_token}"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.content[:2] == b"PK"


def test_viewer_cannot_view_submissions(
    client,
    viewer_token,
) -> None:
    response = client.get("/api/submissions", headers={"Authorization": f"Bearer {viewer_token}"})
    assert response.status_code == 403
