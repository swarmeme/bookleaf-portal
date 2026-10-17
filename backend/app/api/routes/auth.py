from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.api.deps import AUTH_COOKIE_NAME, CurrentUser, DbSession
from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, response: Response, db: DbSession):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    # Same message for unknown email and wrong password, so the endpoint
    # can't be used to discover which emails have accounts.
    if user is None or not verify_password(body.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    token = create_access_token(user.id, user.role)
    response.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        max_age=settings.jwt_expiry_minutes * 60,
        httponly=True,  # not readable from JavaScript, so XSS can't steal it
        samesite="lax",  # not sent on cross-site POSTs, which blocks CSRF
        secure=settings.cookie_secure,
    )
    return LoginResponse(user=UserOut.model_validate(user), access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(AUTH_COOKIE_NAME)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
