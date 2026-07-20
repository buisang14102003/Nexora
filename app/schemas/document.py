from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    original_filename: str
    mime_type: str
    source_type: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
