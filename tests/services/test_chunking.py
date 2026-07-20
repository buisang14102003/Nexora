from uuid import UUID

import pytest

from app.services.chunking import chunk_pages, get_tokenizer
from app.services.parsers import ExtractedPage


DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000001")


class CharacterEncoding:
    def __init__(self, text: str) -> None:
        self.ids = [ord(character) for character in text]
        self.offsets = [(index, index + 1) for index in range(len(text))]


class CharacterTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False) -> CharacterEncoding:
        assert add_special_tokens is False
        return CharacterEncoding(text)


def test_local_byte_tokenizer_never_uses_pretrained_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def network_access(_: str) -> object:
        raise AssertionError("Tokenizer resolution must not access the network")

    monkeypatch.setattr(
        "app.services.chunking.Tokenizer.from_pretrained",
        network_access,
    )

    tokenizer = get_tokenizer("local-byte")

    assert len(tokenizer.encode("Việt Nam").ids) == len("Việt Nam".encode("utf-8"))


def test_tokenizer_requires_a_local_file_or_the_local_byte_mode() -> None:
    with pytest.raises(ValueError, match="local tokenizer file"):
        get_tokenizer("Qwen/Qwen3-Embedding-0.6B")


def test_chunk_retains_page_source_and_offsets() -> None:
    pages = [
        ExtractedPage(
            page_number=3,
            text="one two three four five",
            source_name="policy.pdf",
            source_type="pdf",
        )
    ]

    chunks = chunk_pages(
        pages,
        document_id=DOCUMENT_ID,
        tokenizer=CharacterTokenizer(),
        chunk_size_tokens=100,
        chunk_overlap_tokens=10,
    )

    assert [chunk.text for chunk in chunks] == ["one two three four five"]
    assert chunks[0].document_id == DOCUMENT_ID
    assert chunks[0].page_number == 3
    assert chunks[0].source_name == "policy.pdf"
    assert chunks[0].source_type == "pdf"
    assert (chunks[0].start_offset, chunks[0].end_offset) == (0, 23)


def test_whitespace_free_chunks_are_token_bounded_with_token_overlap() -> None:
    tokenizer = CharacterTokenizer()
    pages = [ExtractedPage(page_number=1, text="abcdefghij")]

    chunks = chunk_pages(
        pages,
        document_id=DOCUMENT_ID,
        tokenizer=tokenizer,
        chunk_size_tokens=5,
        chunk_overlap_tokens=2,
    )

    assert [chunk.text for chunk in chunks] == ["abcde", "defgh", "ghij"]
    assert all(len(tokenizer.encode(chunk.text).ids) <= 5 for chunk in chunks)
    assert chunks[0].text[-2:] == chunks[1].text[:2]
    assert chunks[1].text[-2:] == chunks[2].text[:2]
    assert [(chunk.start_offset, chunk.end_offset) for chunk in chunks] == [
        (0, 5),
        (3, 8),
        (6, 10),
    ]


def test_chunk_ids_are_stable_for_reindexing() -> None:
    pages = [ExtractedPage(page_number=1, text="stable content")]

    first = chunk_pages(
        pages,
        document_id=DOCUMENT_ID,
        tokenizer=CharacterTokenizer(),
        chunk_size_tokens=100,
        chunk_overlap_tokens=10,
    )
    second = chunk_pages(
        pages,
        document_id=DOCUMENT_ID,
        tokenizer=CharacterTokenizer(),
        chunk_size_tokens=100,
        chunk_overlap_tokens=10,
    )

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]


def test_chunking_rejects_overlap_that_cannot_advance() -> None:
    pages = [ExtractedPage(page_number=1, text="content")]

    try:
        chunk_pages(
            pages,
            document_id=DOCUMENT_ID,
            tokenizer=CharacterTokenizer(),
            chunk_size_tokens=2,
            chunk_overlap_tokens=2,
        )
    except ValueError as error:
        assert "overlap" in str(error).lower()
    else:
        raise AssertionError("Expected invalid overlap to be rejected")


def test_chunking_rejects_explicit_zero_size() -> None:
    pages = [ExtractedPage(page_number=1, text="content")]

    try:
        chunk_pages(
            pages,
            document_id=DOCUMENT_ID,
            tokenizer=CharacterTokenizer(),
            chunk_size_tokens=0,
            chunk_overlap_tokens=0,
        )
    except ValueError as error:
        assert "size" in str(error).lower()
    else:
        raise AssertionError("Expected zero chunk size to be rejected")
