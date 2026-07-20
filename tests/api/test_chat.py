from uuid import UUID

from fastapi.testclient import TestClient

from app.rag.graph import AnswerDelta, ChatResult
from app.schemas.chat import Citation


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _workspace(client: TestClient, token: str) -> str:
    response = client.post("/workspaces", headers=_headers(token), json={"name": "Support"})
    assert response.status_code == 201
    return response.json()["id"]


def test_chat_streams_answer_tokens_before_citations(client, register_and_login, monkeypatch) -> None:
    from app.api.routers import chat

    token = register_and_login("admin@example.test")
    workspace_id = _workspace(client, token)
    citation = Citation(
        document_id=UUID("00000000-0000-0000-0000-000000000020"),
        source_name="refund-policy.pdf",
        page_number=3,
        chunk_id=UUID("00000000-0000-0000-0000-000000000030"),
    )
    monkeypatch.setattr(
        chat,
        "run_chat_stream",
        lambda **_: iter(
            [
                AnswerDelta("Refunds are "),
                AnswerDelta("available within 30 days."),
                ChatResult(answer="Refunds are available within 30 days.", citations=[citation]),
            ]
        ),
    )

    response = client.post(
        f"/workspaces/{workspace_id}/chat",
        headers=_headers(token),
        json={"question": "What is the refund policy?"},
    )

    assert response.status_code == 200
    events = [line for line in response.text.splitlines() if line.startswith("event:")]
    assert events == ["event: answer", "event: answer", "event: citations"]
    assert '"delta":"Refunds are "' in response.text
    assert '"page_number":3' in response.text


def test_non_member_cannot_chat_in_another_workspace(client, register_and_login) -> None:
    owner_token = register_and_login("owner@example.test")
    workspace_id = _workspace(client, owner_token)
    other_token = register_and_login("other@example.test")

    response = client.post(
        f"/workspaces/{workspace_id}/chat",
        headers=_headers(other_token),
        json={"question": "What is the refund policy?"},
    )

    assert response.status_code == 404
