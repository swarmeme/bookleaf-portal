from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    author_id: str | None = None


class LoginResponse(BaseModel):
    user: UserOut
    # Also set as an httpOnly cookie. Returned here for API clients (curl/Postman)
    # that prefer the Authorization header; the web app ignores it.
    access_token: str
