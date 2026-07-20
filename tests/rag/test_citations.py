from uuid import UUID

import pytest

from app.services.chunking import Chunk
from app.services.citations import CitationError, resolve_citations


DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000020")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000030")


def _chunk() -> Chunk:
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


def test_resolve_citations_uses_retrieved_source_and_page() -> None:
    citations = resolve_citations([CHUNK_ID], [_chunk()])

    assert citations[0].document_id == DOCUMENT_ID
    assert citations[0].source_name == "refund-policy.pdf"
    assert citations[0].page_number == 3


def test_resolve_citations_rejects_unknown_chunk_id() -> None:
    with pytest.raises(CitationError):
        resolve_citations([UUID("00000000-0000-0000-0000-000000000099")], [_chunk()])
