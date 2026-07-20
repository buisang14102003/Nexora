from pydantic import BaseModel
from typing import Literal
from uuid import UUID


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str


class MembershipCreate(BaseModel):
    email: str
    role: Literal["admin", "member"]


class MembershipResponse(BaseModel):
    user_id: UUID
    workspace_id: UUID
    role: Literal["admin", "member"]
