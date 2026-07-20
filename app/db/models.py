from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum as SQLAlchemyEnum, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MembershipRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class DocumentStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class IngestionJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


membership_role = SQLAlchemyEnum(
    MembershipRole,
    name="membership_role",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda roles: [role.value for role in roles],
)

document_status = SQLAlchemyEnum(
    DocumentStatus,
    name="document_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda statuses: [status.value for status in statuses],
)

ingestion_job_status = SQLAlchemyEnum(
    IngestionJobStatus,
    name="ingestion_job_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda statuses: [status.value for status in statuses],
)


class TimestampedModel:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampedModel, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)


class Workspace(TimestampedModel, Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class Membership(TimestampedModel, Base):
    __tablename__ = "memberships"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id"), primary_key=True
    )
    role: Mapped[MembershipRole] = mapped_column(membership_role, nullable=False)


class Document(TimestampedModel, Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(document_status, nullable=False)
    csv_schema: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    csv_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class IngestionJob(TimestampedModel, Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    status: Mapped[IngestionJobStatus] = mapped_column(
        ingestion_job_status, nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
