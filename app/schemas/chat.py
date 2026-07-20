from uuid import UUID

from pydantic import BaseModel, Field

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


class CsvAnalysisRequest(BaseModel):
    document_id: UUID
    operation: CsvOperation
