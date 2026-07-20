from uuid import UUID

from app.rag.graph import INSUFFICIENT_EVIDENCE, run_graph_for_test
from app.services.chunking import Chunk


DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000020")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000030")


def _page_3_chunk() -> Chunk:
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


def test_graph_returns_insufficient_evidence_without_retrieved_chunks() -> None:
    result = run_graph_for_test(question="Who is the CEO?", retrieved_chunks=[])

    assert result.answer == INSUFFICIENT_EVIDENCE
    assert result.citations == []


def test_answer_citation_references_retrieved_page() -> None:
    result = run_graph_for_test(
        question="What is the refund policy?", retrieved_chunks=[_page_3_chunk()]
    )

    assert result.citations[0].page_number == 3
    assert result.citations[0].source_name == "refund-policy.pdf"


def test_graph_only_cites_chunk_ids_selected_by_the_answer() -> None:
    second_chunk = _page_3_chunk().__class__(
        id=UUID("00000000-0000-0000-0000-000000000031"),
        document_id=DOCUMENT_ID,
        page_number=4,
        text="A different policy detail.",
        source_name="refund-policy.pdf",
        source_type="pdf",
        start_offset=0,
        end_offset=26,
    )

    result = run_graph_for_test(
        question="What is the refund policy?",
        retrieved_chunks=[_page_3_chunk(), second_chunk],
        generated_response=(
            "Refunds are available within 30 days.\n"
            f"<CITATIONS>[\"{CHUNK_ID}\"]</CITATIONS>"
        ),
    )

    assert [citation.chunk_id for citation in result.citations] == [CHUNK_ID]


def test_graph_returns_insufficient_evidence_when_answer_has_no_valid_citation() -> None:
    result = run_graph_for_test(
        question="What is the refund policy?",
        retrieved_chunks=[_page_3_chunk()],
        generated_response="Refunds are available within 30 days.\n<CITATIONS>[]</CITATIONS>",
    )

    assert result.answer == INSUFFICIENT_EVIDENCE
    assert result.citations == []


def test_graph_rejects_citation_outside_retrieved_evidence() -> None:
    result = run_graph_for_test(
        question="What is the refund policy?",
        retrieved_chunks=[_page_3_chunk()],
        generated_response=(
            "Refunds are available within 30 days.\n"
            '<CITATIONS>["00000000-0000-0000-0000-000000000099"]</CITATIONS>'
        ),
    )

    assert result.answer == INSUFFICIENT_EVIDENCE
    assert result.citations == []
