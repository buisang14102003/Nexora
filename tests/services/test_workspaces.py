from contextlib import contextmanager
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import Membership, MembershipRole, User, Workspace
from app.services import workspaces
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


@pytest.fixture
def database_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("JWT_SECRET", "test")
    get_settings.cache_clear()

    from app.db import session

    yield session
    get_settings.cache_clear()


def test_request_rolls_back_workspace_when_membership_creation_fails(
    monkeypatch: pytest.MonkeyPatch,
    database_session,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    owner_id = UUID("00000000-0000-0000-0000-000000000001")

    with Session(engine) as session:
        session.add(User(id=owner_id, email="owner@example.test", password_hash="hash"))
        session.commit()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
    )

    def membership_creation_fails(**_: object) -> Membership:
        raise RuntimeError("membership creation failed")

    monkeypatch.setattr(workspaces, "Membership", membership_creation_fails)

    with pytest.raises(RuntimeError, match="membership creation failed"):
        with contextmanager(database_session.get_session)() as session:
            create_workspace(session, owner_id, "Engineering")

    with Session(engine) as session:
        workspace_count = session.scalar(select(func.count()).select_from(Workspace))
        membership_count = session.scalar(select(func.count()).select_from(Membership))

    assert workspace_count == 0
    assert membership_count == 0


def test_request_rolls_back_workspace_when_later_work_fails(
    monkeypatch: pytest.MonkeyPatch,
    database_session,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    owner_id = UUID("00000000-0000-0000-0000-000000000001")

    with Session(engine) as session:
        session.add(User(id=owner_id, email="owner@example.test", password_hash="hash"))
        session.commit()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
    )

    with pytest.raises(RuntimeError, match="request failed"):
        with contextmanager(database_session.get_session)() as session:
            create_workspace(session, owner_id, "Engineering")
            raise RuntimeError("request failed")

    with Session(engine) as session:
        workspace_count = session.scalar(select(func.count()).select_from(Workspace))
        membership_count = session.scalar(select(func.count()).select_from(Membership))

    assert workspace_count == 0
    assert membership_count == 0
