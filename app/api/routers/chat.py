import json
from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user, require_workspace_membership
from app.db.models import Membership, User
from app.rag.graph import run_chat
from app.schemas.chat import ChatRequest


router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["chat"])


def _events(answer: str, citations: list[dict[str, object]]) -> Iterator[str]:
    yield f"event: answer\ndata: {json.dumps({'answer': answer}, separators=(',', ':'))}\n\n"
    yield f"event: citations\ndata: {json.dumps({'citations': citations}, separators=(',', ':'))}\n\n"


@router.post("/chat")
def chat(
    workspace_id: UUID,
    request: ChatRequest,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    result = run_chat(
        workspace_id=workspace_id,
        user_id=user.id,
        question=request.question,
        document_ids=request.document_ids,
        route=request.route,
    )
    return StreamingResponse(
        _events(result.answer, [citation.model_dump(mode="json") for citation in result.citations]),
        media_type="text/event-stream",
    )
