from collections.abc import Sequence
from uuid import UUID

from app.schemas.chat import Citation
from app.services.chunking import Chunk


class CitationError(ValueError):
    """Raised when an answer tries to cite evidence that was not retrieved."""


def resolve_citations(chunk_ids: Sequence[UUID], chunks: Sequence[Chunk]) -> list[Citation]:
    chunks_by_id = {chunk.id: chunk for chunk in chunks}
    citations: list[Citation] = []
    for chunk_id in dict.fromkeys(chunk_ids):
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            raise CitationError("Citation does not refer to retrieved evidence")
        citations.append(
            Citation(
                document_id=chunk.document_id,
                source_name=chunk.source_name,
                page_number=chunk.page_number,
                chunk_id=chunk.id,
            )
        )
    return citations
