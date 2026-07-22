import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.rag.graph import INSUFFICIENT_EVIDENCE, run_graph_for_test
from app.services.chunking import Chunk


DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000020")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000030")


def _page_3_chunk() -> Chunk:
    return Chunk(
        id=CHUNK_ID,
        document_id=DOCUMENT_ID,
        page_number=3,
        text="Refunds are available within 30 days.",
        source_name="refund-policy.pdf",
        source_type="pdf",
        start_offset=0,
        end_offset=38,
    )


def test_graph_returns_insufficient_evidence_without_retrieved_chunks() -> None:
    result = run_graph_for_test(question="Who is the CEO?", retrieved_chunks=[])

    assert result.answer == INSUFFICIENT_EVIDENCE
    assert result.citations == []


def test_answer_citation_references_retrieved_page() -> None:
    result = run_graph_for_test(
        question="What is the refund policy?", retrieved_chunks=[_page_3_chunk()]
    )

    assert result.citations[0].page_number == 3
    assert result.citations[0].source_name == "refund-policy.pdf"


def test_graph_only_cites_chunk_ids_selected_by_the_answer() -> None:
    second_chunk = _page_3_chunk().__class__(
        id=UUID("00000000-0000-0000-0000-000000000031"),
        document_id=DOCUMENT_ID,
        page_number=4,
        text="A different policy detail.",
        source_name="refund-policy.pdf",
        source_type="pdf",
        start_offset=0,
        end_offset=26,
    )

    result = run_graph_for_test(
        question="What is the refund policy?",
        retrieved_chunks=[_page_3_chunk(), second_chunk],
        generated_response=(
            "Refunds are available within 30 days.\n"
            f"<CITATIONS>[\"{CHUNK_ID}\"]</CITATIONS>"
        ),
    )

    assert [citation.chunk_id for citation in result.citations] == [CHUNK_ID]


def test_graph_returns_insufficient_evidence_when_answer_has_no_valid_citation() -> None:
    result = run_graph_for_test(
        question="What is the refund policy?",
        retrieved_chunks=[_page_3_chunk()],
        generated_response="Refunds are available within 30 days.\n<CITATIONS>[]</CITATIONS>",
    )

    assert result.answer == INSUFFICIENT_EVIDENCE
    assert result.citations == []


def test_graph_uses_retrieved_source_when_local_model_omits_citation_tag() -> None:
    result = run_graph_for_test(
        question="What is the refund policy?",
        retrieved_chunks=[_page_3_chunk()],
        generated_response="Refunds are available within 30 days.",
    )

    assert result.answer == "Refunds are available within 30 days."
    assert [citation.chunk_id for citation in result.citations] == [CHUNK_ID]


def test_graph_rejects_citation_outside_retrieved_evidence() -> None:
    result = run_graph_for_test(
        question="What is the refund policy?",
        retrieved_chunks=[_page_3_chunk()],
        generated_response=(
            "Refunds are available within 30 days.\n"
            '<CITATIONS>["00000000-0000-0000-0000-000000000099"]</CITATIONS>'
        ),
    )

    assert result.answer == INSUFFICIENT_EVIDENCE
    assert result.citations == []


class _FakeCompiledGraph:
    def __init__(self, state: dict[str, object]) -> None:
        self._state = state

    def invoke(self, _: dict[str, object]) -> dict[str, object]:
        return self._state


class _FakeTrace:
    def __init__(self, metadata: dict[str, str]) -> None:
        self.metadata = metadata

    def __enter__(self) -> "_FakeTrace":
        return self

    def __exit__(self, *_: object) -> bool:
        return False


@pytest.mark.parametrize("route", ["document_rag", "summary"])
def test_run_chat_traces_each_graph_route_without_raw_question(
    monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    import app.rag.graph as graph

    traces: list[_FakeTrace] = []
    chunk = _page_3_chunk()
    monkeypatch.setattr(
        graph,
        "build_graph",
        lambda *_: _FakeCompiledGraph(
            {
                "retrieved_chunks": [chunk],
                "answer": "Refunds are available within 30 days.",
                "cited_chunk_ids": [chunk.id],
            }
        ),
    )
    monkeypatch.setattr(
        graph,
        "get_settings",
        lambda: SimpleNamespace(chat_model="gemma3:4b", embedding_model="qwen3-embedding:0.6b"),
    )

    def trace(_: str, metadata: dict[str, str]) -> _FakeTrace:
        result = _FakeTrace(metadata)
        traces.append(result)
        return result

    monkeypatch.setattr(graph, "trace_graph_run", trace)

    graph.run_chat(uuid4(), uuid4(), "private question", route=route)

    assert len(traces) == 1
    assert traces[0].metadata["route"] == route
    assert traces[0].metadata["chat_model"] == "gemma3:4b"
    assert traces[0].metadata["embedding_model"] == "qwen3-embedding:0.6b"
    assert json.loads(traces[0].metadata["chunk_ids"]) == [str(chunk.id)]
    assert "question" not in traces[0].metadata


def test_streaming_chat_traces_its_graph_run(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.rag.graph as graph

    traces: list[_FakeTrace] = []
    monkeypatch.setattr(
        graph,
        "build_graph",
        lambda *_: _FakeCompiledGraph(
            {
                "retrieved_chunks": [],
                "answer": INSUFFICIENT_EVIDENCE,
                "cited_chunk_ids": [],
            }
        ),
    )
    monkeypatch.setattr(
        graph,
        "get_settings",
        lambda: SimpleNamespace(chat_model="gemma3:4b", embedding_model="qwen3-embedding:0.6b"),
    )
    monkeypatch.setattr(
        graph,
        "trace_graph_run",
        lambda _, metadata: traces.append(_FakeTrace(metadata)) or traces[-1],
    )

    list(graph.run_chat_stream(uuid4(), uuid4(), "private question"))

    assert len(traces) == 1
    assert traces[0].metadata["route"] == "document_rag"
    assert json.loads(traces[0].metadata["chunk_ids"]) == []
    assert "question" not in traces[0].metadata
