"""Dependencia que protege endpoints: get_current_user.

HTTPBearer hace que Swagger UI muestre el boton "Authorize".
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security.jwt import decode_token

# auto_error=False -> nosotros devolvemos siempre 401 con un mensaje claro
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Pega aqui el access_token devuelto por POST /auth/login",
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """AUTENTICACION: responde 'quien es este usuario?' a partir del JWT."""
    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = int(payload["sub"])
    except ExpiredSignatureError:
        raise _unauthorized("Token has expired")
    except (JWTError, ValueError):
        raise _unauthorized("Invalid token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return user
