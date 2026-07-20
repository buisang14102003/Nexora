from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from minio import Minio
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document, DocumentStatus, IngestionJob, IngestionJobStatus


SUPPORTED_UPLOADS = {
    ".csv": ("text/csv", "csv"),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
    ),
    ".pdf": ("application/pdf", "pdf"),
    ".png": ("image/png", "image"),
    ".jpg": ("image/jpeg", "image"),
    ".jpeg": ("image/jpeg", "image"),
}


def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def store_upload(workspace_id: UUID, file: UploadFile, session: Session) -> Document:
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    supported_upload = SUPPORTED_UPLOADS.get(extension)
    if supported_upload is None or file.content_type != supported_upload[0]:
        raise ValueError("Unsupported file type")

    contents = file.file.read(get_settings().upload_max_bytes + 1)
    if len(contents) > get_settings().upload_max_bytes:
        raise ValueError("Upload exceeds the configured size limit")
    if not contents:
        raise ValueError("Upload is empty")

    document_id = uuid4()
    object_key = f"{workspace_id}/{document_id}/{filename}"
    client = get_minio_client()
    settings = get_settings()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
    client.put_object(
        settings.minio_bucket,
        object_key,
        BytesIO(contents),
        len(contents),
        content_type=file.content_type,
    )

    document = Document(
        id=document_id,
        workspace_id=workspace_id,
        original_filename=filename,
        mime_type=file.content_type,
        object_key=object_key,
        source_type=supported_upload[1],
        status=DocumentStatus.QUEUED,
    )
    session.add(document)
    session.add(
        IngestionJob(
            workspace_id=workspace_id,
            document_id=document_id,
            status=IngestionJobStatus.QUEUED,
        )
    )
    session.flush()
    return document
