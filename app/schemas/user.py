from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50, examples=["student01"])
    full_name: str = Field(min_length=1, max_length=150, examples=["Ana Torres"])
    email: EmailStr = Field(examples=["ana@example.com"])
    password: str = Field(min_length=8, examples=["MySecurePassword123!"])

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        # bcrypt solo procesa los primeros 72 bytes: rechazamos mas en vez de truncar
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes long")
        return value


class UserLogin(BaseModel):
    email: EmailStr = Field(examples=["ana@example.com"])
    password: str = Field(examples=["MySecurePassword123!"])
    remember_me: bool = Field(
        default=False,
        description="Si es true, el refresh token dura mas (30 dias en vez de 7).",
    )


class UserResponse(BaseModel):
    """Nunca incluye password_hash."""

    id: int
    username: str
    full_name: str | None = None
    email: EmailStr
    auth_provider: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos de vida del access token")


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
