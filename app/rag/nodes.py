import json
from collections.abc import Callable
from typing import TypedDict
from uuid import UUID

from app.rag.prompts import answer_prompt
from app.services.chunking import Chunk
from app.services.vector_store import QdrantVectorStore


class GraphState(TypedDict, total=False):
    workspace_id: UUID
    user_id: UUID
    question: str
    route: str
    document_ids: list[UUID] | None
    retrieved_chunks: list[Chunk]
    answer: str
    cited_chunk_ids: list[UUID]


AnswerGenerator = Callable[[str], str]
_CITATION_START = "<CITATIONS>"
_CITATION_END = "</CITATIONS>"
_INSUFFICIENT_EVIDENCE = "I could not find that information in this workspace's documents."


def parse_model_response(response: str) -> tuple[str, list[UUID]]:
    answer_text, marker, remainder = response.partition(_CITATION_START)
    citation_payload, end_marker, _ = remainder.partition(_CITATION_END)
    if not marker or not end_marker:
        return _INSUFFICIENT_EVIDENCE, []
    try:
        parsed = json.loads(citation_payload)
        if not isinstance(parsed, list) or not all(isinstance(value, str) for value in parsed):
            raise ValueError
        cited_chunk_ids = [UUID(value) for value in parsed]
    except (ValueError, TypeError, json.JSONDecodeError):
        return _INSUFFICIENT_EVIDENCE, []
    clean_answer = answer_text.strip()
    if not clean_answer or clean_answer == _INSUFFICIENT_EVIDENCE:
        return _INSUFFICIENT_EVIDENCE, []
    return clean_answer, cited_chunk_ids


def retrieve(
    state: GraphState,
    vector_store: QdrantVectorStore,
) -> GraphState:
    document_ids = state.get("document_ids")
    if document_ids:
        points = vector_store.search(
            state["question"], workspace_id=state["workspace_id"], document_ids=document_ids
        )
    else:
        points = vector_store.search(state["question"], workspace_id=state["workspace_id"])
    chunks = [
        Chunk(
            id=UUID(str(point.payload["chunk_id"])),
            document_id=UUID(str(point.payload["document_id"])),
            page_number=int(point.payload["page_number"] or 0),
            text=str(point.payload["text"]),
            source_name=str(point.payload["source_name"]),
            source_type=str(point.payload["source_type"]),
            start_offset=0,
            end_offset=len(str(point.payload["text"])),
        )
        for point in points
        if point.payload is not None
    ]
    return {"retrieved_chunks": chunks}


def answer(state: GraphState, generator: AnswerGenerator) -> GraphState:
    chunks = state.get("retrieved_chunks", [])
    if not chunks:
        return {"answer": "I could not find that information in this workspace's documents."}
    evidence = "\n\n".join(
        f"[chunk_id={chunk.id}; source={chunk.source_name}; page={chunk.page_number}]\n{chunk.text}"
        for chunk in chunks
    )
    response = generator(answer_prompt(state["question"], evidence, state.get("route", "document_rag")))
    answer_text, cited_chunk_ids = parse_model_response(response)
    return {"answer": answer_text, "cited_chunk_ids": cited_chunk_ids}
