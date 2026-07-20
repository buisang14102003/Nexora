from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentStatus, IngestionJob, IngestionJobStatus
from app.services.chunking import chunk_pages
from app.services.parsers import DocumentExtractionError, extract_document
from app.services.vector_store import QdrantVectorStore, VectorStoreError


def claim_next_job(session: Session) -> IngestionJob | None:
    job = session.scalar(
        select(IngestionJob)
        .where(IngestionJob.status == IngestionJobStatus.QUEUED)
        .order_by(IngestionJob.created_at, IngestionJob.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        return None

    job.status = IngestionJobStatus.PROCESSING
    job.attempts += 1
    job.claimed_at = datetime.now(timezone.utc)
    document = session.get(Document, job.document_id)
    if document is None:
        raise RuntimeError("Ingestion job document does not exist")
    document.status = DocumentStatus.PROCESSING
    session.flush()
    return job


def process_claimed_job(
    session: Session,
    job: IngestionJob,
    vector_store: QdrantVectorStore | None = None,
) -> None:
    document = session.get(Document, job.document_id)
    if document is None:
        raise RuntimeError("Ingestion job document does not exist")

    pages = extract_document(document)
    chunks = chunk_pages(pages, document_id=document.id)
    if document.source_type != "csv" and not chunks:
        raise DocumentExtractionError("Document contains no extractable text")
    if chunks:
        (vector_store or QdrantVectorStore()).index_chunks(
            document.workspace_id,
            document.id,
            chunks,
        )

    document.status = DocumentStatus.READY
    job.status = IngestionJobStatus.READY
    job.error_message = None
    session.flush()


def fail_job(session: Session, job: IngestionJob, error: Exception) -> None:
    document = session.get(Document, job.document_id)
    if document is not None:
        document.status = DocumentStatus.FAILED
    job.status = IngestionJobStatus.FAILED
    job.error_message = _safe_failure_reason(error)
    session.flush()


def _safe_failure_reason(error: Exception) -> str:
    if isinstance(error, DocumentExtractionError):
        return "Document extraction failed"
    if isinstance(error, VectorStoreError):
        return "Document indexing failed"
    return "Document ingestion failed"
