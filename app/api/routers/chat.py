import json
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_workspace_membership
from app.core.config import get_settings
from app.core.observability import trace_graph_run
from app.db import session as db_session
from app.db.models import ChatMessage, ChatSession, Membership, User
from app.rag.graph import AnswerDelta, ChatResult, run_chat_stream
from app.schemas.chat import ChatRequest, CsvAnalysisRequest
from app.services.csv_analysis import (
    CsvResult,
    CsvSourceNotFound,
    InvalidCsvOperation,
    run_csv_operation,
)


router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["chat"])


def _events(
    events: Iterator[AnswerDelta | ChatResult],
    chat_session: ChatSession | None = None,
) -> Iterator[str]:
    answer_parts: list[str] = []
    final_answer: str | None = None
    final_citations: list[dict[str, object]] = []
    for event in events:
        if isinstance(event, AnswerDelta):
            answer_parts.append(event.text)
            yield f"event: answer\ndata: {json.dumps({'delta': event.text}, separators=(',', ':'))}\n\n"
        else:
            citations = [citation.model_dump(mode="json") for citation in event.citations]
            final_answer = event.answer
            final_citations = citations
            if not citations:
                yield (
                    "event: answer\ndata: "
                    f"{json.dumps({'answer': event.answer, 'replace': True}, separators=(',', ':'))}\n\n"
                )
            yield f"event: citations\ndata: {json.dumps({'citations': citations}, separators=(',', ':'))}\n\n"

    if chat_session is not None and final_answer is not None:
        with db_session.SessionLocal.begin() as message_session:
            message_session.add(
                ChatMessage(
                    session_id=chat_session.id,
                    role="assistant",
                    content=final_answer or "".join(answer_parts),
                    citations=final_citations,
                    created_at=datetime.now(timezone.utc),
                )
            )
            message_session.execute(
                ChatSession.__table__.update()
                .where(ChatSession.id == chat_session.id)
                .values(updated_at=func.now())
            )


@router.post("/chat")
def chat(
    workspace_id: UUID,
    request: ChatRequest,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> StreamingResponse:
    chat_session: ChatSession | None = None
    if request.session_id is not None:
        chat_session = session.scalar(
            select(ChatSession).where(
                ChatSession.id == request.session_id,
                ChatSession.workspace_id == workspace_id,
                ChatSession.user_id == user.id,
            )
        )
        if chat_session is None:
            raise HTTPException(status_code=404, detail="Chat session not found")

        if chat_session.title == "New chat":
            chat_session.title = request.question.strip()[:80]
        chat_session.updated_at = func.now()
        session.add(
            ChatMessage(
                session_id=chat_session.id,
                role="user",
                content=request.question,
                citations=[],
                created_at=datetime.now(timezone.utc),
            )
        )
        session.flush()

    events = run_chat_stream(
        workspace_id=workspace_id,
        user_id=user.id,
        question=request.question,
        document_ids=request.document_ids,
        route=request.route,
    )
    return StreamingResponse(
        _events(events, chat_session),
        media_type="text/event-stream",
    )


@router.post("/csv-analysis", response_model=CsvResult)
def csv_analysis(
    workspace_id: UUID,
    request: CsvAnalysisRequest,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> CsvResult:
    try:
        settings = get_settings()
        with trace_graph_run(
            "csv_analysis",
            {
                "route": "csv_analysis",
                "workspace_id": str(workspace_id),
                "chat_model": settings.chat_model,
                "embedding_model": settings.embedding_model,
            },
        ):
            return run_csv_operation(
                document_id=request.document_id,
                workspace_id=workspace_id,
                operation=request.operation,
                session=session,
            )
    except CsvSourceNotFound as exc:
        raise HTTPException(status_code=404, detail="CSV document not found") from exc
    except InvalidCsvOperation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
