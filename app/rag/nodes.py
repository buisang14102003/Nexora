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


AnswerGenerator = Callable[[str], str]


def retrieve(
    state: GraphState,
    vector_store: QdrantVectorStore,
) -> GraphState:
    document_ids = state.get("document_ids")
    if document_ids and len(document_ids) == 1:
        points = vector_store.search(
            state["question"], workspace_id=state["workspace_id"], document_id=document_ids[0]
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
    if document_ids:
        allowed = set(document_ids)
        chunks = [chunk for chunk in chunks if chunk.document_id in allowed]
    return {"retrieved_chunks": chunks}


def answer(state: GraphState, generator: AnswerGenerator) -> GraphState:
    chunks = state.get("retrieved_chunks", [])
    if not chunks:
        return {"answer": "I could not find that information in this workspace's documents."}
    evidence = "\n\n".join(
        f"[chunk_id={chunk.id}; source={chunk.source_name}; page={chunk.page_number}]\n{chunk.text}"
        for chunk in chunks
    )
    return {"answer": generator(answer_prompt(state["question"], evidence, state.get("route", "document_rag")))}
