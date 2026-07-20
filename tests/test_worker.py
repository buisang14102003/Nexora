from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import Document, DocumentStatus, IngestionJob, IngestionJobStatus
from app.services import jobs
from app.services.chunking import Chunk
from app.services.parsers import ExtractedPage
from worker.main import run_once


class FakeVectorStore:
    def __init__(self) -> None:
        self.indexed: list[tuple[object, object, list[Chunk]]] = []

    def index_chunks(self, workspace_id, document_id, chunks: list[Chunk]) -> None:
        self.indexed.append((workspace_id, document_id, chunks))


def _session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _queued_document(session: Session) -> Document:
    document = Document(
        workspace_id=uuid4(),
        original_filename="guide.pdf",
        mime_type="application/pdf",
        object_key="workspace/guide.pdf",
        source_type="pdf",
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


def test_worker_claims_indexes_and_marks_document_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, factory = _session_factory()
    with factory.begin() as session:
        document = _queued_document(session)
        document_id = document.id
        workspace_id = document.workspace_id

    monkeypatch.setattr(
        jobs,
        "extract_document",
        lambda _: [
            ExtractedPage(
                page_number=1,
                text="ready to index",
                source_name="guide.pdf",
                source_type="pdf",
            )
        ],
    )
    store = FakeVectorStore()

    assert run_once(session_factory=factory, vector_store=store) is True

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
    assert store.indexed[0][2][0].page_number == 1
    engine.dispose()


def test_worker_marks_safe_failure_without_leaking_exception_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, factory = _session_factory()
    with factory.begin() as session:
        document_id = _queued_document(session).id

    def fail_extraction(_: Document) -> list[ExtractedPage]:
        raise RuntimeError("secret document content")

    monkeypatch.setattr(jobs, "extract_document", fail_extraction)

    assert run_once(session_factory=factory, vector_store=FakeVectorStore()) is True

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
