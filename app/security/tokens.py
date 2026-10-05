"""Emision de pares access + refresh y registro de la sesion en la base de datos."""
from sqlalchemy.orm import Session

from app.config import ACCESS_TOKEN_MINUTES
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import TokenResponse
from app.security.jwt import create_access_token, create_refresh_token, hash_token


def issue_token_pair(db: Session, user: User, remember_me: bool = False) -> TokenResponse:
    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id, remember_me)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at.replace(tzinfo=None),  # UTC sin tzinfo
            remember_me=remember_me,
        )
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_MINUTES * 60,
    )
