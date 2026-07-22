from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Membership, MembershipRole, Workspace


class WorkspaceNameConflictError(Exception):
    pass


def create_workspace(session: Session, owner_id: UUID, name: str) -> Workspace:
    slug = "-".join(name.lower().split())
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
