from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol
from uuid import UUID, uuid5

from tokenizers import Encoding, Tokenizer

from app.core.config import get_settings
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


class TextTokenizer(Protocol):
    def encode(
        self,
        sequence: str,
        add_special_tokens: bool = False,
    ) -> Encoding: ...


@lru_cache
def get_tokenizer(name: str) -> TextTokenizer:
    return Tokenizer.from_pretrained(name)


def chunk_pages(
    pages: list[ExtractedPage],
    document_id: UUID,
    *,
    tokenizer: TextTokenizer | None = None,
    chunk_size_tokens: int | None = None,
    chunk_overlap_tokens: int | None = None,
) -> list[Chunk]:
    settings = (
        get_settings()
        if tokenizer is None
        or chunk_size_tokens is None
        or chunk_overlap_tokens is None
        else None
    )
    active_tokenizer = tokenizer or get_tokenizer(settings.embedding_tokenizer)
    size = settings.chunk_size_tokens if chunk_size_tokens is None else chunk_size_tokens
    overlap = (
        settings.chunk_overlap_tokens
        if chunk_overlap_tokens is None
        else chunk_overlap_tokens
    )
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("Chunk overlap must be non-negative and smaller than chunk size")

    chunks: list[Chunk] = []
    for page in pages:
        token_offsets = active_tokenizer.encode(
            page.text,
            add_special_tokens=False,
        ).offsets
        start_token = 0
        while start_token < len(token_offsets):
            end_token = min(start_token + size, len(token_offsets))
            start_offset = token_offsets[start_token][0]
            end_offset = token_offsets[end_token - 1][1]
            while end_token > start_token and len(
                active_tokenizer.encode(
                    page.text[start_offset:end_offset],
                    add_special_tokens=False,
                ).ids
            ) > size:
                end_token -= 1
                end_offset = token_offsets[end_token - 1][1]
            if end_token == start_token:
                raise ValueError("Tokenizer offsets cannot produce a bounded chunk")
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
            if end_token == len(token_offsets):
                break
            start_token = end_token - overlap
    return chunks
