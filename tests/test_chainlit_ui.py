from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import chainlit_app
from app.chainlit_client import LocalRagApi


class _Response:
    def __init__(self, content: str = "") -> None:
        self.content = content
        self.id: str | None = None
        self.tokens: list[str] = []
        self.updates = 0

    async def send(self):
        self.id = "sent"
        return self

    async def stream_token(self, token: str) -> None:
        assert self.id, "Chainlit messages must be sent before streaming"
        self.tokens.append(token)

    async def update(self) -> None:
        assert self.id, "Chainlit messages must be sent before updating"
        self.updates += 1


class _StreamingApi:
    async def stream_chat(self, *_args):
        yield "answer", {"delta": "A cited answer"}
        yield "citations", {"citations": [{"source_name": "guide.pdf", "page_number": 1}]}


def test_chat_sends_response_before_streaming_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _Response()
    monkeypatch.setattr(chainlit_app, "_api", lambda: _StreamingApi())
    monkeypatch.setattr(
        chainlit_app,
        "_session",
        lambda name, default=None: {"token": "jwt", "workspace_id": "workspace", "route": "document_rag"}.get(name, default),
    )
    monkeypatch.setattr(chainlit_app.cl, "Message", lambda content="", **_kwargs: response)

    asyncio.run(chainlit_app.chat(SimpleNamespace(content="Question", elements=[])))

    assert response.tokens == ["A cited answer"]
    assert "guide.pdf" in response.content
    assert response.updates == 1


def test_csv_analysis_client_posts_only_to_fastapi(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict]] = []

    async def request(self, method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {
            "values": [{"sum_amount": 120}],
            "evidence": {
                "source_name": "sales.csv",
                "columns": ["amount"],
                "filters": [],
                "row_range": "2-4",
                "row_count": 3,
            },
        }

    monkeypatch.setattr(LocalRagApi, "_request", request)
    result = asyncio.run(
        LocalRagApi("http://api").csv_analysis(
            "jwt", "workspace", "document", {"aggregations": [{"column": "amount", "function": "sum"}]}
        )
    )

    assert calls == [
        (
            "POST",
            "/workspaces/workspace/csv-analysis",
            {
                "token": "jwt",
                "json": {"document_id": "document", "operation": {"aggregations": [{"column": "amount", "function": "sum"}]}},
            },
        )
    ]
    assert result["values"] == [{"sum_amount": 120}]


def test_csv_result_renders_values_and_evidence() -> None:
    content = chainlit_app._csv_result_content(
        {
            "values": [{"sum_amount": 120}],
            "evidence": {
                "source_name": "sales.csv",
                "columns": ["amount"],
                "filters": [{"column": "country", "operator": "eq", "value": "VN"}],
                "row_range": "2-4",
                "row_count": 3,
            },
        }
    )

    assert "sum_amount" in content
    assert "sales.csv" in content
    assert "amount" in content
    assert "country" in content
    assert "2-4" in content


def test_csv_selection_action_is_offered_for_ready_csv_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[SimpleNamespace] = []

    class _Message:
        def __init__(self, content: str, actions=None) -> None:
            self.content = content
            self.actions = actions or []
            messages.append(self)

        async def send(self):
            return self

    class _Api:
        async def list_documents(self, *_args):
            return [
                {"id": "ready-csv", "original_filename": "sales.csv", "source_type": "csv", "status": "ready"},
                {"id": "pending-csv", "original_filename": "later.csv", "source_type": "csv", "status": "pending"},
            ]

    monkeypatch.setattr(chainlit_app, "_api", lambda: _Api())
    monkeypatch.setattr(chainlit_app, "_session", lambda name, default=None: {"token": "jwt", "workspace_id": "workspace"}.get(name, default))
    monkeypatch.setattr(chainlit_app.cl, "Message", _Message)

    asyncio.run(chainlit_app._show_csv_analysis_actions())

    assert [(action.name, action.payload) for action in messages[0].actions] == [
        ("select_csv_analysis", {"id": "ready-csv", "name": "sales.csv"})
    ]
