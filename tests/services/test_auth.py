import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError
from app.core.security import hash_password, require_role, verify_password
from app.db.base import Base
from app.db.models import Membership, MembershipRole
from app.services.auth import create_user


def test_password_hash_never_equals_plaintext() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)


def test_member_cannot_be_treated_as_admin() -> None:
    membership = Membership(role=MembershipRole.MEMBER)

    with pytest.raises(ForbiddenError):
        require_role(membership, {"admin"})


def test_create_user_stores_a_password_hash() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = create_user(session, "user@example.test", "correct horse battery staple")

        assert user.email == "user@example.test"
        assert verify_password("correct horse battery staple", user.password_hash)
