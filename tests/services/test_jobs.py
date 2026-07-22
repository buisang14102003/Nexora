from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Document, DocumentStatus, IngestionJob, IngestionJobStatus
from app.services.jobs import claim_next_job


def test_claimed_job_is_not_claimed_twice() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        document = Document(
            workspace_id=uuid4(),
            original_filename="guide.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            object_key="workspace/guide.docx",
            source_type="docx",
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
        session.commit()

        first = claim_next_job(session)
        second = claim_next_job(session)

    assert first is not None
    assert first.status is IngestionJobStatus.PROCESSING
    assert first.attempts == 1
    assert first.claimed_at is not None
    assert second is None


def test_claim_next_job_reclaims_a_stale_processing_job() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime(2026, 7, 22, tzinfo=timezone.utc)

    with Session(engine) as session:
        document = Document(
            workspace_id=uuid4(),
            original_filename="guide.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            object_key="workspace/guide.docx",
            source_type="docx",
            status=DocumentStatus.PROCESSING,
        )
        session.add(document)
        session.flush()
        job = IngestionJob(
            workspace_id=document.workspace_id,
            document_id=document.id,
            status=IngestionJobStatus.PROCESSING,
            attempts=1,
            claimed_at=now - timedelta(minutes=16),
        )
        session.add(job)
        session.commit()

        claimed = claim_next_job(session, now=now)

    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status is IngestionJobStatus.PROCESSING
    assert claimed.attempts == 2
    assert claimed.claimed_at == now
