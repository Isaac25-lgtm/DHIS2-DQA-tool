"""DHIS2 session login/logout must be restricted to MANAGER accounts only.

These tests pin the manager-only DHIS2 governance posture so the assessor
flow cannot regress into auto-pulling or sharing the in-memory DHIS2 session.
"""
from __future__ import annotations


def test_assessor_cannot_sign_in_to_dhis2(client, assessor_token) -> None:
    response = client.post(
        "/api/dhis2/session/login",
        headers={"Authorization": f"Bearer {assessor_token}"},
        json={
            "base_url": "https://hmis.health.go.ug/api",
            "username": "field_user",
            "password": "secret-password-12",
        },
    )
    assert response.status_code == 403


def test_assessor_cannot_sign_out_of_dhis2(client, assessor_token) -> None:
    response = client.post(
        "/api/dhis2/session/logout",
        headers={"Authorization": f"Bearer {assessor_token}"},
    )
    assert response.status_code == 403


def test_reviewer_cannot_sign_in_to_dhis2(client, reviewer_token) -> None:
    response = client.post(
        "/api/dhis2/session/login",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={
            "base_url": "https://hmis.health.go.ug/api",
            "username": "reviewer",
            "password": "secret-password-12",
        },
    )
    assert response.status_code == 403


def test_unauthenticated_dhis2_login_is_rejected(client) -> None:
    response = client.post(
        "/api/dhis2/session/login",
        json={
            "base_url": "https://hmis.health.go.ug/api",
            "username": "x",
            "password": "secret-password-12",
        },
    )
    assert response.status_code in {401, 403}
