import json
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from queue import Queue
from threading import Thread
from uuid import UUID

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.core.observability import trace_graph_run
from app.rag.nodes import AnswerGenerator, GraphState, answer, retrieve
from app.schemas.chat import Citation
from app.services.chunking import Chunk
from app.services.citations import CitationError, resolve_citations
from app.services.vector_store import QdrantVectorStore


INSUFFICIENT_EVIDENCE = "I could not find that information in this workspace's documents."


@dataclass(frozen=True)
class ChatResult:
    answer: str
    citations: list[Citation]


@dataclass(frozen=True)
class AnswerDelta:
    text: str


_CITATION_START = "<CITATIONS>"


def _ollama_generator(prompt: str) -> str:
    settings = get_settings()
    result = ChatOllama(model=settings.chat_model, base_url=settings.ollama_base_url).invoke(prompt)
    content = result.content
    return content if isinstance(content, str) else str(content)


class _StreamingResponseParser:
    def __init__(self, on_delta: Callable[[str], None]) -> None:
        self._on_delta = on_delta
        self._raw: list[str] = []
        self._pending = ""
        self._in_citations = False

    def feed(self, text: str) -> None:
        self._raw.append(text)
        if self._in_citations:
            return
        self._pending += text
        marker_at = self._pending.find(_CITATION_START)
        if marker_at >= 0:
            self._emit(self._pending[:marker_at])
            self._pending = ""
            self._in_citations = True
            return
        safe_length = max(0, len(self._pending) - len(_CITATION_START) + 1)
        self._emit(self._pending[:safe_length])
        self._pending = self._pending[safe_length:]

    def finish(self) -> str:
        if not self._in_citations:
            self._emit(self._pending)
        return "".join(self._raw)

    def _emit(self, text: str) -> None:
        if text:
            self._on_delta(text)


def _ollama_stream_generator(on_delta: Callable[[str], None]) -> AnswerGenerator:
    def generate(prompt: str) -> str:
        settings = get_settings()
        parser = _StreamingResponseParser(on_delta)
        for result in ChatOllama(
            model=settings.chat_model, base_url=settings.ollama_base_url
        ).stream(prompt):
            content = result.content
            parser.feed(content if isinstance(content, str) else str(content))
        return parser.finish()

    return generate


def build_graph(vector_store: QdrantVectorStore, generator: AnswerGenerator):
    graph = StateGraph(GraphState)
    graph.add_node("retrieve", lambda state: retrieve(state, vector_store))
    graph.add_node("answer", lambda state: answer(state, generator))
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


def _result_from_state(state: GraphState) -> ChatResult:
    chunks = state.get("retrieved_chunks", [])
    answer_text = state.get("answer", INSUFFICIENT_EVIDENCE)
    cited_chunk_ids = state.get("cited_chunk_ids", [])
    if not chunks or answer_text == INSUFFICIENT_EVIDENCE or not cited_chunk_ids:
        return ChatResult(answer=INSUFFICIENT_EVIDENCE, citations=[])
    try:
        citations = resolve_citations(cited_chunk_ids, chunks)
    except CitationError:
        return ChatResult(answer=INSUFFICIENT_EVIDENCE, citations=[])
    return ChatResult(answer=answer_text, citations=citations)


def _invoke_graph(
    workspace_id: UUID,
    user_id: UUID,
    question: str,
    document_ids: list[UUID] | None,
    route: str,
    generator: AnswerGenerator,
) -> GraphState:
    settings = get_settings()
    with trace_graph_run(
        "rag_graph",
        {
            "route": route,
            "workspace_id": str(workspace_id),
            "chat_model": settings.chat_model,
            "embedding_model": settings.embedding_model,
            "chunk_ids": "",
        },
    ) as trace:
        state = build_graph(QdrantVectorStore(), generator).invoke(
            {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "question": question,
                "route": route,
                "document_ids": document_ids,
            }
        )
        trace.metadata["chunk_ids"] = json.dumps(
            [str(chunk.id) for chunk in state.get("retrieved_chunks", [])]
        )
        return state


def run_chat(
    workspace_id: UUID,
    user_id: UUID,
    question: str,
    document_ids: list[UUID] | None = None,
    *,
    route: str = "document_rag",
) -> ChatResult:
    if route not in {"document_rag", "summary"}:
        raise ValueError("Unsupported chat route")
    state = _invoke_graph(
        workspace_id,
        user_id,
        question,
        document_ids,
        route,
        _ollama_generator,
    )
    return _result_from_state(state)


def run_chat_stream(
    workspace_id: UUID,
    user_id: UUID,
    question: str,
    document_ids: list[UUID] | None = None,
    *,
    route: str = "document_rag",
) -> Iterator[AnswerDelta | ChatResult]:
    if route not in {"document_rag", "summary"}:
        raise ValueError("Unsupported chat route")
    queue: Queue[AnswerDelta | ChatResult | Exception | None] = Queue()

    def emit(text: str) -> None:
        queue.put(AnswerDelta(text))

    def invoke_graph() -> None:
        try:
            state = _invoke_graph(
                workspace_id,
                user_id,
                question,
                document_ids,
                route,
                _ollama_stream_generator(emit),
            )
            queue.put(_result_from_state(state))
        except Exception as error:
            queue.put(error)
        finally:
            queue.put(None)

    Thread(target=invoke_graph, daemon=True).start()

    def events() -> Iterator[AnswerDelta | ChatResult]:
        while (event := queue.get()) is not None:
            if isinstance(event, Exception):
                raise event
            yield event

    return events()


def run_graph_for_test(
    question: str,
    retrieved_chunks: Sequence[Chunk],
    generated_response: str | None = None,
) -> ChatResult:
    """Runs the answer half of the real graph with deterministic evidence for unit tests."""

    graph = StateGraph(GraphState)
    response = generated_response or (
        f"{retrieved_chunks[0].text}\n<CITATIONS>[\"{retrieved_chunks[0].id}\"]</CITATIONS>"
        if retrieved_chunks
        else INSUFFICIENT_EVIDENCE
    )
    graph.add_node("answer", lambda state: answer(state, lambda _: response))
    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)
    state = graph.compile().invoke(
        {"question": question, "route": "document_rag", "retrieved_chunks": list(retrieved_chunks)}
    )
    return _result_from_state(state)
