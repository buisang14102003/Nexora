from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_workspace_membership
from app.db.models import ChatMessage, ChatSession, Membership, User
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionDetailResponse,
    ChatSessionRename,
    ChatSessionResponse,
)


router = APIRouter(prefix="/workspaces/{workspace_id}/chat-sessions", tags=["chat-sessions"])


def _owned_session(
    session: Session, workspace_id: UUID, user_id: UUID, session_id: UUID
) -> ChatSession:
    chat_session = session.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.workspace_id == workspace_id,
            ChatSession.user_id == user_id,
        )
    )
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat_session


@router.get("", response_model=list[ChatSessionResponse])
def list_sessions(
    workspace_id: UUID,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[ChatSession]:
    return list(
        session.scalars(
            select(ChatSession)
            .where(ChatSession.workspace_id == workspace_id, ChatSession.user_id == user.id)
            .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
        )
    )


@router.post("", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    workspace_id: UUID,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    request: ChatSessionCreate = ChatSessionCreate(),
) -> ChatSession:
    chat_session = ChatSession(workspace_id=workspace_id, user_id=user.id, title=request.title)
    session.add(chat_session)
    session.flush()
    return chat_session


@router.get("/{session_id}", response_model=ChatSessionDetailResponse)
def get_chat_session(
    workspace_id: UUID,
    session_id: UUID,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ChatSessionDetailResponse:
    chat_session = _owned_session(session, workspace_id, user.id, session_id)
    messages = list(
        session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
    )
    return ChatSessionDetailResponse(
        **ChatSessionResponse.model_validate(chat_session).model_dump(), messages=messages
    )


@router.patch("/{session_id}", response_model=ChatSessionResponse)
def rename_session(
    workspace_id: UUID,
    session_id: UUID,
    request: ChatSessionRename,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ChatSession:
    chat_session = _owned_session(session, workspace_id, user.id, session_id)
    chat_session.title = request.title
    session.flush()
    return chat_session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    workspace_id: UUID,
    session_id: UUID,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    chat_session = _owned_session(session, workspace_id, user.id, session_id)
    session.query(ChatMessage).filter(ChatMessage.session_id == chat_session.id).delete()
    session.delete(chat_session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
