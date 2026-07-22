from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_workspace_membership
from app.core.errors import ForbiddenError
from app.core.security import require_role
from app.db.models import Membership, MembershipRole, User, Workspace
from app.schemas.workspace import MembershipCreate, MembershipResponse, WorkspaceCreate, WorkspaceResponse
from app.services.workspaces import WorkspaceNameConflictError, create_workspace


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def require_workspace_admin(
    membership: Annotated[Membership, Depends(require_workspace_membership)],
) -> Membership:
    try:
        require_role(membership, {"admin"})
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail="Admin role required") from exc
    return membership


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create(
    workspace: WorkspaceCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Workspace:
    try:
        return create_workspace(session, user.id, workspace.name)
    except WorkspaceNameConflictError as exc:
        raise HTTPException(status_code=409, detail="Workspace name already exists") from exc


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[Workspace]:
    return list(
        session.scalars(
            select(Workspace)
            .join(Membership, Membership.workspace_id == Workspace.id)
            .where(Membership.user_id == user.id)
            .order_by(Workspace.created_at, Workspace.id)
        )
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: UUID,
    membership: Annotated[Membership, Depends(require_workspace_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> Workspace:
    workspace = session.get(Workspace, membership.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post(
    "/{workspace_id}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    membership_request: MembershipCreate,
    workspace_id: UUID,
    _: Annotated[Membership, Depends(require_workspace_admin)],
    session: Annotated[Session, Depends(get_session)],
) -> Membership:
    user = session.scalar(select(User).where(User.email == membership_request.email))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing_membership = session.get(
        Membership, {"user_id": user.id, "workspace_id": workspace_id}
    )
    if existing_membership is not None:
        raise HTTPException(status_code=409, detail="User is already a workspace member")

    membership = Membership(
        user_id=user.id,
        workspace_id=workspace_id,
        role=MembershipRole(membership_request.role),
    )
    session.add(membership)
    session.flush()
    return membership
