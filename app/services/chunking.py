import re
from dataclasses import dataclass
import os
from uuid import UUID, uuid5

from app.services.parsers import ExtractedPage


@dataclass(frozen=True)
class Chunk:
    id: UUID
    document_id: UUID
    page_number: int
    text: str
    source_name: str
    source_type: str
    start_offset: int
    end_offset: int


def chunk_pages(
    pages: list[ExtractedPage],
    document_id: UUID,
    *,
    chunk_size_tokens: int | None = None,
    chunk_overlap_tokens: int | None = None,
) -> list[Chunk]:
    size = (
        int(os.getenv("CHUNK_SIZE_TOKENS", "400"))
        if chunk_size_tokens is None
        else chunk_size_tokens
    )
    overlap = (
        int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))
        if chunk_overlap_tokens is None
        else chunk_overlap_tokens
    )
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("Chunk overlap must be non-negative and smaller than chunk size")

    chunks: list[Chunk] = []
    for page in pages:
        tokens = list(re.finditer(r"\S+", page.text))
        start_token = 0
        while start_token < len(tokens):
            end_token = min(start_token + size, len(tokens))
            start_offset = tokens[start_token].start()
            end_offset = tokens[end_token - 1].end()
            chunk_id = uuid5(
                document_id,
                f"{page.page_number}:{page.source_name}:{start_offset}:{end_offset}",
            )
            chunks.append(
                Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    page_number=page.page_number,
                    text=page.text[start_offset:end_offset],
                    source_name=page.source_name,
                    source_type=page.source_type,
                    start_offset=start_offset,
                    end_offset=end_offset,
                )
            )
            if end_token == len(tokens):
                break
            start_token = end_token - overlap
    return chunks
