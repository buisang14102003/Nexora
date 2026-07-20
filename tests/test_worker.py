from io import BytesIO
from uuid import uuid4

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.db.models import Document, DocumentStatus, IngestionJob, IngestionJobStatus
from app.services import jobs, parsers
from app.services.chunking import Chunk
from app.services.parsers import ExtractedPage
from worker.main import run_once


class FakeVectorStore:
    def __init__(self) -> None:
        self.indexed: list[tuple[object, object, list[Chunk]]] = []

    def index_chunks(self, workspace_id, document_id, chunks: list[Chunk]) -> None:
        self.indexed.append((workspace_id, document_id, chunks))


class CharacterEncoding:
    def __init__(self, text: str) -> None:
        self.ids = [ord(character) for character in text]
        self.offsets = [(index, index + 1) for index in range(len(text))]


class CharacterTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False) -> CharacterEncoding:
        assert add_special_tokens is False
        return CharacterEncoding(text)


def _session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _text_pdf_bytes(text: str) -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()
    return output.getvalue()


def _queued_document(
    session: Session,
    *,
    filename: str = "guide.pdf",
    source_type: str = "pdf",
) -> Document:
    document = Document(
        workspace_id=uuid4(),
        original_filename=filename,
        mime_type="application/octet-stream",
        object_key=f"workspace/{filename}",
        source_type=source_type,
        status=DocumentStatus.QUEUED,
    )
    session.add(document)
    session.flush()
    session.add(
        IngestionJob(
            workspace_id=document.workspace_id,
            document_id=document.id,
            status=IngestionJobStatus.QUEUED,
        )
    )
    return document


def test_worker_uses_settings_and_real_parser_metadata_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, factory = _session_factory()
    with factory.begin() as session:
        document = _queued_document(session)
        document_id = document.id
        workspace_id = document.workspace_id

    monkeypatch.setattr(
        parsers,
        "_load_document_bytes",
        lambda _: _text_pdf_bytes("abcdefghij"),
    )
    tokenizer_names: list[str] = []

    def fake_get_tokenizer(name: str) -> CharacterTokenizer:
        tokenizer_names.append(name)
        return CharacterTokenizer()

    monkeypatch.setattr(jobs, "get_tokenizer", fake_get_tokenizer, raising=False)
    settings = Settings(
        database_url="sqlite://",
        jwt_secret="test-secret",
        embedding_tokenizer="custom/tokenizer",
        chunk_size_tokens=5,
        chunk_overlap_tokens=2,
    )
    store = FakeVectorStore()

    assert run_once(
        session_factory=factory,
        vector_store=store,
        settings=settings,
    ) is True

    with factory() as session:
        persisted_document = session.get(Document, document_id)
        persisted_job = session.scalar(select(IngestionJob))
        assert persisted_document is not None
        assert persisted_document.status is DocumentStatus.READY
        assert persisted_job is not None
        assert persisted_job.status is IngestionJobStatus.READY
        assert persisted_job.attempts == 1
        assert persisted_job.error_message is None
    assert store.indexed[0][0:2] == (workspace_id, document_id)
    chunks = store.indexed[0][2]
    assert tokenizer_names == ["custom/tokenizer"]
    assert [chunk.text for chunk in chunks] == ["abcde", "defgh", "ghij"]
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert all(chunk.source_name == "guide.pdf" for chunk in chunks)
    assert all(chunk.source_type == "pdf" for chunk in chunks)
    engine.dispose()


def test_worker_marks_csv_ready_without_loading_a_tokenizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, factory = _session_factory()
    with factory.begin() as session:
        document_id = _queued_document(
            session,
            filename="sales.csv",
            source_type="csv",
        ).id

    monkeypatch.setattr(
        parsers,
        "_load_document_bytes",
        lambda _: b"country,amount\nVN,1250\n",
    )

    def unexpected_tokenizer_load(_: str) -> CharacterTokenizer:
        raise AssertionError("CSV processing must not load an embedding tokenizer")

    monkeypatch.setattr(jobs, "get_tokenizer", unexpected_tokenizer_load)
    store = FakeVectorStore()

    assert run_once(
        session_factory=factory,
        vector_store=store,
        settings=Settings(database_url="sqlite://", jwt_secret="test-secret"),
    ) is True

    with factory() as session:
        document = session.get(Document, document_id)
        job = session.scalar(select(IngestionJob))
        assert document is not None
        assert document.status is DocumentStatus.READY
        assert document.csv_row_count == 1
        assert job is not None
        assert job.status is IngestionJobStatus.READY
    assert store.indexed == []
    engine.dispose()


def test_worker_marks_safe_failure_without_leaking_exception_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, factory = _session_factory()
    with factory.begin() as session:
        document_id = _queued_document(session).id

    def fail_extraction(
        _: Document,
        *,
        settings: Settings,
    ) -> list[ExtractedPage]:
        raise RuntimeError("secret document content")

    monkeypatch.setattr(jobs, "extract_document", fail_extraction)

    assert run_once(
        session_factory=factory,
        vector_store=FakeVectorStore(),
        settings=Settings(database_url="sqlite://", jwt_secret="test-secret"),
        tokenizer=CharacterTokenizer(),
    ) is True

    with factory() as session:
        document = session.get(Document, document_id)
        job = session.scalar(select(IngestionJob))
        assert document is not None
        assert document.status is DocumentStatus.FAILED
        assert job is not None
        assert job.status is IngestionJobStatus.FAILED
        assert job.error_message == "Document ingestion failed"
        assert "secret" not in job.error_message
    engine.dispose()


def test_worker_returns_false_when_queue_is_empty() -> None:
    engine, factory = _session_factory()

    assert run_once(session_factory=factory, vector_store=FakeVectorStore()) is False

    engine.dispose()
