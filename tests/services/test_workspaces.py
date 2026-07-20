from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Membership, MembershipRole, User, Workspace
from app.services.workspaces import create_workspace


def test_create_workspace_adds_owner_as_admin() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    owner_id = UUID("00000000-0000-0000-0000-000000000001")

    with Session(engine) as session:
        session.add(User(id=owner_id, email="owner@example.test", password_hash="hash"))
        session.commit()

        assert session.get(User, owner_id) is not None
        workspace = create_workspace(session, owner_id, "Engineering")

        membership = session.scalar(
            select(Membership).where(
                Membership.user_id == owner_id,
                Membership.workspace_id == workspace.id,
            )
        )

        stored_workspace = session.scalar(
            select(Workspace).where(Workspace.id == workspace.id)
        )

    assert workspace.name == "Engineering"
    assert membership is not None
    assert membership.role is MembershipRole.ADMIN
    assert stored_workspace is not None
