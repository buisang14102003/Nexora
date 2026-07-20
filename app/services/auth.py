from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User


def create_user(session: Session, email: str, password: str) -> User:
    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
