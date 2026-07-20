from collections.abc import Generator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Membership, User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_session() -> Generator[Session, None, None]:
    from app.db.session import get_session as get_database_session

    yield from get_database_session()


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[get_settings().jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError) as exc:
        raise credentials_exception from exc

    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


def require_workspace_membership(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Membership:
    membership = session.get(
        Membership, {"user_id": user.id, "workspace_id": workspace_id}
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return membership
