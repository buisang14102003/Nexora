from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Membership, MembershipRole, Workspace


def create_workspace(session: Session, owner_id: UUID, name: str) -> Workspace:
    workspace = Workspace(name=name, slug="-".join(name.lower().split()))

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
