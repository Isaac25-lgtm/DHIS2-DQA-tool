def test_login_with_seeded_manager(client, seeded_manager) -> None:
    response = client.post(
        "/api/auth/login",
        json={
            "email": seeded_manager.email,
            "password": "ChangeMe123!",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == seeded_manager.email
    assert payload["user"]["role"] == "MANAGER"


def test_protected_endpoint_without_token_fails(client) -> None:
    response = client.get("/api/users")
    assert response.status_code == 401

