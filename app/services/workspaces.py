from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Membership, MembershipRole, Workspace


class WorkspaceNameConflictError(Exception):
    pass


class ArchivedWorkspaceUpdateError(Exception):
    pass


def workspace_slug(name: str) -> str:
    return "-".join(name.lower().split())


def create_workspace(session: Session, owner_id: UUID, name: str) -> Workspace:
    slug = workspace_slug(name)
    if session.scalar(select(Workspace).where(Workspace.slug == slug)) is not None:
        raise WorkspaceNameConflictError

    workspace = Workspace(name=name, slug=slug)

    session.add(workspace)
    session.flush()
    session.add(
        Membership(
            user_id=owner_id,
            workspace_id=workspace.id,
            role=MembershipRole.ADMIN,
        )
    )
    session.flush()

    return workspace


def update_workspace(
    session: Session,
    workspace: Workspace,
    *,
    name: str | None = None,
    is_pinned: bool | None = None,
) -> Workspace:
    if workspace.archived_at is not None:
        raise ArchivedWorkspaceUpdateError
    if name is not None and name != workspace.name:
        slug = workspace_slug(name)
        conflict = session.scalar(
            select(Workspace).where(
                Workspace.slug == slug,
                Workspace.id != workspace.id,
            )
        )
        if conflict is not None:
            raise WorkspaceNameConflictError
        workspace.name = name
        workspace.slug = slug
    if is_pinned is not None:
        workspace.is_pinned = is_pinned
    session.flush()
    session.refresh(workspace)
    return workspace


def archive_workspace(session: Session, workspace: Workspace) -> Workspace:
    if workspace.archived_at is None:
        workspace.archived_at = datetime.now(UTC)
        workspace.is_pinned = False
        session.flush()
        session.refresh(workspace)
    return workspace


def restore_workspace(session: Session, workspace: Workspace) -> Workspace:
    if workspace.archived_at is not None:
        workspace.archived_at = None
        workspace.is_pinned = False
        session.flush()
        session.refresh(workspace)
    return workspace
