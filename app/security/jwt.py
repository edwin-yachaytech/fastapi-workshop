"""Creacion y validacion de JWT (access y refresh)."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt  # noqa: F401  (JWTError se reexporta para los routers)

from app.config import (
    ACCESS_TOKEN_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET,
    REFRESH_TOKEN_DAYS,
    REMEMBER_REFRESH_TOKEN_DAYS,
)


def _encode(user_id: int, token_type: str, lifetime: timedelta) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expire = now + lifetime
    payload = {
        "sub": str(user_id),
        "type": token_type,          # distingue access de refresh
        "jti": uuid.uuid4().hex,     # identificador unico del token
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expire


def create_access_token(user_id: int) -> str:
    token, _ = _encode(user_id, "access", timedelta(minutes=ACCESS_TOKEN_MINUTES))
    return token


def create_refresh_token(user_id: int, remember_me: bool = False) -> tuple[str, datetime]:
    """Remember Me NO alarga el access token: solo alarga la vida del refresh token."""
    days = REMEMBER_REFRESH_TOKEN_DAYS if remember_me else REFRESH_TOKEN_DAYS
    return _encode(user_id, "refresh", timedelta(days=days))


def decode_token(token: str, expected_type: str, verify_exp: bool = True) -> dict:
    """Valida firma, expiracion y tipo. Lanza JWTError (o ExpiredSignatureError) si falla."""
    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"verify_exp": verify_exp},
    )
    if payload.get("type") != expected_type:
        raise JWTError(f"Expected a {expected_type} token")
    if "sub" not in payload:
        raise JWTError("Token has no subject")
    return payload


def hash_token(token: str) -> str:
    """SHA-256 del token: en la BD guardamos esto, nunca el token en claro."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
