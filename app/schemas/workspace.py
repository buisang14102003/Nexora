from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Workspace name is required")
        return normalized


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_pinned: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Workspace name is required")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "WorkspaceUpdate":
        if self.name is None and self.is_pinned is None:
            raise ValueError("At least one workspace field is required")
        return self


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_pinned: bool
    archived_at: datetime | None
    updated_at: datetime


class MembershipCreate(BaseModel):
    email: str
    role: Literal["admin", "member"]


class MembershipResponse(BaseModel):
    user_id: UUID
    workspace_id: UUID
    role: Literal["admin", "member"]
