def test_manager_can_create_indicator(client, manager_token) -> None:
    response = client.post(
        "/api/indicators",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "indicator_name": "Test Indicator",
            "indicator_group": "Maternity",
            "hmis_code": "TEST-001",
            "dhis2_uid_or_operand": "AbcDef12345",
            "dataset_name": "HMIS 105:02-03",
            "hmis_section": "Maternity",
            "source_register": "Maternity register",
            "category_combo": None,
            "value_type": "integer",
            "is_active": True,
            "is_required_by_default": True,
            "default_discrepancy_threshold_percent": 5,
            "is_death_indicator": False,
            "sort_order": 1,
            "notes": "Prompt 2 test indicator",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["indicator_name"] == "Test Indicator"
    assert payload["data_element_uid"] == "AbcDef12345"
    assert payload["category_option_combo_uid"] is None


def test_viewer_cannot_create_indicator(client, viewer_token) -> None:
    response = client.post(
        "/api/indicators",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "indicator_name": "Forbidden Indicator",
            "indicator_group": "Maternity",
            "hmis_code": "TEST-002",
            "dhis2_uid_or_operand": "AbcDef67890",
            "dataset_name": "HMIS 105:02-03",
            "hmis_section": "Maternity",
            "source_register": "Maternity register",
            "category_combo": None,
            "value_type": "integer",
            "is_active": True,
            "is_required_by_default": True,
            "default_discrepancy_threshold_percent": 5,
            "is_death_indicator": False,
            "sort_order": 1,
            "notes": "Prompt 2 forbidden indicator",
        },
    )

    assert response.status_code == 403
