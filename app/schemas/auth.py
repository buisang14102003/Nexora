from pydantic import BaseModel
from uuid import UUID


class UserCredentials(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
