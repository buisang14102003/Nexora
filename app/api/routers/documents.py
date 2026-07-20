from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session, require_workspace_membership
from app.db.models import Document, Membership
from app.schemas.document import DocumentResponse
from app.services.storage import store_upload


router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    workspace_id: UUID,
    file: Annotated[UploadFile, File()],
    _: Annotated[Membership, Depends(require_workspace_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> Document:
    try:
        return store_upload(workspace_id, file, session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    workspace_id: UUID,
    _: Annotated[Membership, Depends(require_workspace_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> list[Document]:
    return list(
        session.scalars(
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(Document.created_at, Document.id)
        )
    )
