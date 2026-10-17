"""Authentication and role-based access dependencies used by every protected route."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models import User
from app.models.enums import UserRole

AUTH_COOKIE_NAME = "access_token"

DbSession = Annotated[Session, Depends(get_db)]


def _extract_token(request: Request) -> str | None:
    # The browser app authenticates with an httpOnly cookie (EventSource can't send
    # headers, cookies work everywhere). API clients may use "Authorization: Bearer".
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(AUTH_COOKIE_NAME)


def get_current_user(request: Request, db: DbSession) -> User:
    token = _extract_token(request)
    if not token:
        raise UnauthorizedError("Please log in to continue")

    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedError("Your session has expired. Please log in again")

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise UnauthorizedError("Account no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("This action is only available to the BookLeaf team")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
