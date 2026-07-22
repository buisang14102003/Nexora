from fastapi.testclient import TestClient


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_user_can_create_and_list_their_workspace(
    client: TestClient, register_and_login
) -> None:
    token = register_and_login("owner@example.test")

    create_response = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Engineering"}
    )
    list_response = client.get("/workspaces", headers=_headers(token))

    assert create_response.status_code == 201
    assert create_response.json()["name"] == "Engineering"
    assert list_response.status_code == 200
    assert list_response.json() == [create_response.json()]


def test_duplicate_normalized_workspace_name_returns_conflict(
    client: TestClient, register_and_login
) -> None:
    token = register_and_login("owner@example.test")

    first = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Engineering Team"}
    )
    duplicate = client.post(
        "/workspaces", headers=_headers(token), json={"name": " engineering   team "}
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Workspace name already exists"}


def test_member_cannot_add_workspace_members(
    client: TestClient, register_and_login
) -> None:
    admin_token = register_and_login("admin@example.test")
    workspace_response = client.post(
        "/workspaces", headers=_headers(admin_token), json={"name": "Engineering"}
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    member_token = register_and_login("member@example.test")
    add_member_response = client.post(
        f"/workspaces/{workspace_id}/members",
        headers=_headers(admin_token),
        json={"email": "member@example.test", "role": "member"},
    )
    assert add_member_response.status_code == 201

    response = client.post(
        f"/workspaces/{workspace_id}/members",
        headers=_headers(member_token),
        json={"email": "new@example.test", "role": "member"},
    )

    assert response.status_code == 403


def test_user_cannot_get_another_users_workspace(
    client: TestClient, register_and_login
) -> None:
    owner_token = register_and_login("owner@example.test")
    workspace_response = client.post(
        "/workspaces", headers=_headers(owner_token), json={"name": "Engineering"}
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]

    other_token = register_and_login("other@example.test")
    response = client.get(f"/workspaces/{workspace_id}", headers=_headers(other_token))

    assert response.status_code == 404
    assert response.json() == {"detail": "Workspace not found"}
