from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import get_settings
from app.core.security import verify_password
from app.db.models import User
from app.schemas.auth import TokenResponse, UserCredentials, UserResponse
from app.services.auth import create_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(credentials: UserCredentials, session: Session = Depends(get_session)) -> User:
    existing_user = session.scalar(select(User).where(User.email == credentials.email))
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    return create_user(session, credentials.email, credentials.password)


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserCredentials, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.scalar(select(User).where(User.email == credentials.email))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    access_token = jwt.encode(
        {"sub": str(user.id), "exp": expires_at},
        get_settings().jwt_secret,
        algorithm=get_settings().jwt_algorithm,
    )
    return TokenResponse(access_token=access_token)
