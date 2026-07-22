from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_workspace_membership
from app.core.errors import ForbiddenError
from app.core.security import require_role
from app.db.models import Membership, MembershipRole, User, Workspace
from app.schemas.workspace import (
    MembershipCreate,
    MembershipResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.workspaces import (
    ArchivedWorkspaceUpdateError,
    WorkspaceNameConflictError,
    archive_workspace,
    create_workspace,
    restore_workspace,
    update_workspace,
)


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def require_workspace_admin(
    membership: Annotated[Membership, Depends(require_workspace_membership)],
) -> Membership:
    try:
        require_role(membership, {"admin"})
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail="Admin role required") from exc
    return membership


def workspace_for_user(
    session: Session,
    user_id: UUID,
    workspace_id: UUID,
) -> Workspace:
    workspace = session.scalar(
        select(Workspace)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(
            Membership.user_id == user_id,
            Workspace.id == workspace_id,
        )
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


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
    status_filter: Annotated[
        Literal["active", "archived"], Query(alias="status")
    ] = "active",
) -> list[Workspace]:
    query = (
        select(Workspace)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user.id)
    )
    if status_filter == "active":
        query = query.where(Workspace.archived_at.is_(None)).order_by(
            Workspace.is_pinned.desc(), Workspace.updated_at.desc(), Workspace.id
        )
    else:
        query = query.where(Workspace.archived_at.is_not(None)).order_by(
            Workspace.archived_at.desc(), Workspace.id
        )
    return list(session.scalars(query))


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update(
    workspace_id: UUID,
    request: WorkspaceUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Workspace:
    workspace = workspace_for_user(session, user.id, workspace_id)
    try:
        return update_workspace(
            session,
            workspace,
            name=request.name,
            is_pinned=request.is_pinned,
        )
    except WorkspaceNameConflictError as exc:
        raise HTTPException(status_code=409, detail="Workspace name already exists") from exc
    except ArchivedWorkspaceUpdateError as exc:
        raise HTTPException(
            status_code=409, detail="Archived workspace cannot be updated"
        ) from exc


@router.post("/{workspace_id}/archive", response_model=WorkspaceResponse)
def archive(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Workspace:
    return archive_workspace(session, workspace_for_user(session, user.id, workspace_id))


@router.post("/{workspace_id}/restore", response_model=WorkspaceResponse)
def restore(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Workspace:
    return restore_workspace(session, workspace_for_user(session, user.id, workspace_id))


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
