from uuid import UUID

from app.services.chunking import chunk_pages
from app.services.parsers import ExtractedPage


DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000001")


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
        chunk_size_tokens=3,
        chunk_overlap_tokens=1,
    )

    assert [chunk.text for chunk in chunks] == ["one two three", "three four five"]
    assert chunks[0].document_id == DOCUMENT_ID
    assert chunks[0].page_number == 3
    assert chunks[0].source_name == "policy.pdf"
    assert chunks[0].source_type == "pdf"
    assert (chunks[0].start_offset, chunks[0].end_offset) == (0, 13)
    assert (chunks[1].start_offset, chunks[1].end_offset) == (8, 23)


def test_chunk_ids_are_stable_for_reindexing() -> None:
    pages = [ExtractedPage(page_number=1, text="stable content")]

    first = chunk_pages(pages, document_id=DOCUMENT_ID)
    second = chunk_pages(pages, document_id=DOCUMENT_ID)

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]


def test_chunking_rejects_overlap_that_cannot_advance() -> None:
    pages = [ExtractedPage(page_number=1, text="content")]

    try:
        chunk_pages(
            pages,
            document_id=DOCUMENT_ID,
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
            chunk_size_tokens=0,
            chunk_overlap_tokens=0,
        )
    except ValueError as error:
        assert "size" in str(error).lower()
    else:
        raise AssertionError("Expected zero chunk size to be rejected")
