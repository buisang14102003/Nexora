from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.services.csv_analysis import CsvOperation


class Citation(BaseModel):
    document_id: UUID
    source_name: str
    page_number: int | None = None
    row_range: str | None = None
    chunk_id: UUID | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8_000)
    document_ids: list[UUID] | None = Field(default=None, max_length=20)
    route: str = Field(default="document_rag", pattern="^(document_rag|summary)$")
    session_id: UUID | None = None


class ChatSessionCreate(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=255)


class ChatSessionRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    citations: list[Citation]
    created_at: datetime


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: list[ChatMessageResponse]


class CsvAnalysisRequest(BaseModel):
    document_id: UUID
    operation: CsvOperation
