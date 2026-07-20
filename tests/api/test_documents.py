from io import BytesIO

from fastapi.testclient import TestClient


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_workspace(client: TestClient, token: str) -> str:
    response = client.post(
        "/workspaces", headers=_headers(token), json={"name": "Engineering"}
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_upload_creates_queued_document_and_job(
    client: TestClient, register_and_login, monkeypatch
) -> None:
    from app.services import storage

    stored: list[str] = []

    class FakeMinio:
        def bucket_exists(self, bucket: str) -> bool:
            return True

        def put_object(self, bucket: str, object_key: str, data, length: int, **_: object) -> None:
            stored.append(object_key)

    monkeypatch.setattr(storage, "get_minio_client", lambda: FakeMinio())
    token = register_and_login("admin@example.test")
    workspace_id = _create_workspace(client, token)

    response = client.post(
        f"/workspaces/{workspace_id}/documents",
        headers=_headers(token),
        files={
            "file": (
                "guide.docx",
                b"example document",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["original_filename"] == "guide.docx"
    assert len(stored) == 1

    listed = client.get(f"/workspaces/{workspace_id}/documents", headers=_headers(token))
    assert listed.status_code == 200
    assert listed.json() == [response.json()]


def test_member_can_upload_to_their_workspace(client: TestClient, register_and_login, monkeypatch) -> None:
    from app.services import storage

    class FakeMinio:
        def bucket_exists(self, bucket: str) -> bool:
            return True

        def put_object(self, *_: object, **__: object) -> None:
            pass

    monkeypatch.setattr(storage, "get_minio_client", lambda: FakeMinio())
    admin_token = register_and_login("admin@example.test")
    workspace_id = _create_workspace(client, admin_token)
    member_token = register_and_login("member@example.test")
    member_response = client.post(
        f"/workspaces/{workspace_id}/members",
        headers=_headers(admin_token),
        json={"email": "member@example.test", "role": "member"},
    )
    assert member_response.status_code == 201

    response = client.post(
        f"/workspaces/{workspace_id}/documents",
        headers=_headers(member_token),
        files={"file": ("notes.csv", b"name\nAda\n", "text/csv")},
    )

    assert response.status_code == 202


def test_other_workspace_member_cannot_list_or_upload_documents(
    client: TestClient, register_and_login
) -> None:
    owner_token = register_and_login("owner@example.test")
    workspace_id = _create_workspace(client, owner_token)
    other_token = register_and_login("other@example.test")

    list_response = client.get(
        f"/workspaces/{workspace_id}/documents", headers=_headers(other_token)
    )
    upload_response = client.post(
        f"/workspaces/{workspace_id}/documents",
        headers=_headers(other_token),
        files={"file": ("notes.csv", b"name\nAda\n", "text/csv")},
    )

    assert list_response.status_code == 404
    assert upload_response.status_code == 404


def test_unsupported_upload_is_rejected_before_storage(
    client: TestClient, register_and_login, monkeypatch
) -> None:
    from app.services import storage

    class FakeMinio:
        def put_object(self, *_: object, **__: object) -> None:
            raise AssertionError("unsupported uploads must not be stored")

    monkeypatch.setattr(storage, "get_minio_client", lambda: FakeMinio())
    token = register_and_login("admin@example.test")
    workspace_id = _create_workspace(client, token)

    response = client.post(
        f"/workspaces/{workspace_id}/documents",
        headers=_headers(token),
        files={"file": ("unsafe.exe", b"not a document", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"
