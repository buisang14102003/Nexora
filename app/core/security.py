from pwdlib import PasswordHash

from app.core.errors import ForbiddenError
from app.db.models import Membership


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def require_role(membership: Membership, allowed: set[str]) -> None:
    if membership.role.value not in allowed:
        raise ForbiddenError
