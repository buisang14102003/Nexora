from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.rag.nodes import AnswerGenerator, GraphState, answer, retrieve
from app.schemas.chat import Citation
from app.services.chunking import Chunk
from app.services.citations import resolve_citations
from app.services.vector_store import QdrantVectorStore


INSUFFICIENT_EVIDENCE = "I could not find that information in this workspace's documents."


@dataclass(frozen=True)
class ChatResult:
    answer: str
    citations: list[Citation]


def _ollama_generator(prompt: str) -> str:
    settings = get_settings()
    result = ChatOllama(model=settings.chat_model, base_url=settings.ollama_base_url).invoke(prompt)
    content = result.content
    return content if isinstance(content, str) else str(content)


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
    if not chunks or answer_text == INSUFFICIENT_EVIDENCE:
        return ChatResult(answer=INSUFFICIENT_EVIDENCE, citations=[])
    return ChatResult(answer=answer_text, citations=resolve_citations([chunk.id for chunk in chunks], chunks))


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
    state = build_graph(QdrantVectorStore(), _ollama_generator).invoke(
        {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "question": question,
            "route": route,
            "document_ids": document_ids,
        }
    )
    return _result_from_state(state)


def run_graph_for_test(question: str, retrieved_chunks: Sequence[Chunk]) -> ChatResult:
    """Runs the answer half of the real graph with deterministic evidence for unit tests."""

    graph = StateGraph(GraphState)
    graph.add_node("answer", lambda state: answer(state, lambda _: retrieved_chunks[0].text))
    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)
    state = graph.compile().invoke(
        {"question": question, "route": "document_rag", "retrieved_chunks": list(retrieved_chunks)}
    )
    return _result_from_state(state)
