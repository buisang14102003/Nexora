import json
from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user, require_workspace_membership
from app.db.models import Membership, User
from app.rag.graph import AnswerDelta, ChatResult, run_chat_stream
from app.schemas.chat import ChatRequest


router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["chat"])


def _events(events: Iterator[AnswerDelta | ChatResult]) -> Iterator[str]:
    for event in events:
        if isinstance(event, AnswerDelta):
            yield f"event: answer\ndata: {json.dumps({'delta': event.text}, separators=(',', ':'))}\n\n"
        else:
            citations = [citation.model_dump(mode="json") for citation in event.citations]
            yield f"event: citations\ndata: {json.dumps({'citations': citations}, separators=(',', ':'))}\n\n"


@router.post("/chat")
def chat(
    workspace_id: UUID,
    request: ChatRequest,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    events = run_chat_stream(
        workspace_id=workspace_id,
        user_id=user.id,
        question=request.question,
        document_ids=request.document_ids,
        route=request.route,
    )
    return StreamingResponse(
        _events(events),
        media_type="text/event-stream",
    )
