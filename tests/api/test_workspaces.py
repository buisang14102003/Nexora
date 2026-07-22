from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.db.models import Workspace


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


def test_workspace_persists_pin_and_archive_state(client, register_and_login) -> None:
    from app.db.session import SessionLocal

    token = register_and_login("owner@example.test")
    created = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Research"}
    ).json()

    with SessionLocal.begin() as session:
        workspace = session.get(Workspace, UUID(created["id"]))
        assert workspace is not None
        assert workspace.is_pinned is False
        assert workspace.archived_at is None
        workspace.is_pinned = True
        workspace.archived_at = datetime.now(UTC)

    with SessionLocal() as session:
        persisted = session.get(Workspace, UUID(created["id"]))
        assert persisted is not None
        assert persisted.is_pinned is True
        assert persisted.archived_at is not None


def test_workspace_management_flow(client, register_and_login) -> None:
    token = register_and_login("owner@example.test")
    first = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Engineering"}
    ).json()
    second = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Support"}
    ).json()

    renamed = client.patch(
        f"/workspaces/{first['id']}",
        headers=_headers(token),
        json={"name": "Product research", "is_pinned": True},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Product research"
    assert renamed.json()["is_pinned"] is True
    assert renamed.json()["updated_at"]

    active = client.get("/workspaces?status=active", headers=_headers(token))
    assert active.status_code == 200
    assert active.json()[0]["id"] == first["id"]

    archived = client.post(
        f"/workspaces/{first['id']}/archive", headers=_headers(token)
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"]
    assert archived.json()["is_pinned"] is False
    assert [
        item["id"]
        for item in client.get(
            "/workspaces?status=active", headers=_headers(token)
        ).json()
    ] == [second["id"]]
    assert [
        item["id"]
        for item in client.get(
            "/workspaces?status=archived", headers=_headers(token)
        ).json()
    ] == [first["id"]]

    restored = client.post(
        f"/workspaces/{first['id']}/restore", headers=_headers(token)
    )
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert restored.json()["is_pinned"] is False


def test_archived_workspace_rejects_update(client, register_and_login) -> None:
    token = register_and_login("owner@example.test")
    workspace = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Archive me"}
    ).json()
    client.post(f"/workspaces/{workspace['id']}/archive", headers=_headers(token))

    response = client.patch(
        f"/workspaces/{workspace['id']}",
        headers=_headers(token),
        json={"name": "Hidden", "is_pinned": True},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Archived workspace cannot be updated"}


def test_other_user_cannot_manage_workspace(client, register_and_login) -> None:
    owner_token = register_and_login("owner@example.test")
    workspace = client.post(
        "/workspaces", headers=_headers(owner_token), json={"name": "Private"}
    ).json()
    other_token = register_and_login("other@example.test")

    assert (
        client.patch(
            f"/workspaces/{workspace['id']}",
            headers=_headers(other_token),
            json={"is_pinned": True},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/workspaces/{workspace['id']}/restore", headers=_headers(other_token)
        ).status_code
        == 404
    )
