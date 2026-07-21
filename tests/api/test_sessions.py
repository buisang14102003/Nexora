from uuid import UUID

from fastapi.testclient import TestClient

from app.rag.graph import AnswerDelta, ChatResult
from app.schemas.chat import Citation


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _workspace(client: TestClient, token: str, name: str = "Support") -> str:
    response = client.post("/workspaces", headers=_headers(token), json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def test_chat_session_crud_restores_messages_and_scopes_to_owner(
    client, register_and_login, monkeypatch
) -> None:
    from app.api.routers import chat

    owner_token = register_and_login("owner@example.test")
    workspace_id = _workspace(client, owner_token)
    session_response = client.post(
        f"/workspaces/{workspace_id}/chat-sessions", headers=_headers(owner_token)
    )

    assert session_response.status_code == 201
    session_id = session_response.json()["id"]
    assert session_response.json()["title"] == "New chat"

    citation = Citation(
        document_id=UUID("00000000-0000-0000-0000-000000000020"),
        source_name="refund-policy.pdf",
    )
    monkeypatch.setattr(
        chat,
        "run_chat_stream",
        lambda **_: iter(
            [
                AnswerDelta("Refunds are available."),
                ChatResult(answer="Refunds are available.", citations=[citation]),
            ]
        ),
    )

    chat_response = client.post(
        f"/workspaces/{workspace_id}/chat",
        headers=_headers(owner_token),
        json={"question": "What is the refund policy?", "session_id": session_id},
    )
    assert chat_response.status_code == 200

    selected = client.get(
        f"/workspaces/{workspace_id}/chat-sessions/{session_id}",
        headers=_headers(owner_token),
    )
    assert selected.status_code == 200
    assert selected.json()["title"] == "What is the refund policy?"
    assert [(message["role"], message["content"]) for message in selected.json()["messages"]] == [
        ("user", "What is the refund policy?"),
        ("assistant", "Refunds are available."),
    ]
    assert selected.json()["messages"][1]["citations"] == [citation.model_dump(mode="json")]

    renamed = client.patch(
        f"/workspaces/{workspace_id}/chat-sessions/{session_id}",
        headers=_headers(owner_token),
        json={"title": "Refund policy"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Refund policy"
    assert [item["id"] for item in client.get(
        f"/workspaces/{workspace_id}/chat-sessions", headers=_headers(owner_token)
    ).json()] == [session_id]

    other_token = register_and_login("other@example.test")
    assert client.post(
        f"/workspaces/{workspace_id}/members",
        headers=_headers(owner_token),
        json={"email": "other@example.test", "role": "member"},
    ).status_code == 201
    assert client.get(
        f"/workspaces/{workspace_id}/chat-sessions/{session_id}",
        headers=_headers(other_token),
    ).status_code == 404

    deleted = client.delete(
        f"/workspaces/{workspace_id}/chat-sessions/{session_id}",
        headers=_headers(owner_token),
    )
    assert deleted.status_code == 204
    assert client.get(
        f"/workspaces/{workspace_id}/chat-sessions/{session_id}",
        headers=_headers(owner_token),
    ).status_code == 404


def test_chat_rejects_a_session_from_another_workspace(client, register_and_login) -> None:
    token = register_and_login("owner@example.test")
    first_workspace = _workspace(client, token, "First")
    second_workspace = _workspace(client, token, "Second")
    session_id = client.post(
        f"/workspaces/{first_workspace}/chat-sessions", headers=_headers(token)
    ).json()["id"]

    response = client.post(
        f"/workspaces/{second_workspace}/chat",
        headers=_headers(token),
        json={"question": "Private question", "session_id": session_id},
    )

    assert response.status_code == 404
