def test_manager_can_create_facility(client, manager_token) -> None:
    response = client.post(
        "/api/facilities",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "facility_name": "Masaka HC IV",
            "district": "Masaka",
            "facility_type": "HC IV",
            "ownership": "PNFP",
            "dhis2_org_unit_uid": "abc12345678",
            "notes": "Prompt 2 facility test",
            "is_active": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["facility_name"] == "Masaka HC IV"
    assert payload["district"] == "Masaka"
    assert payload["dhis2_org_unit_uid"] == "abc12345678"

