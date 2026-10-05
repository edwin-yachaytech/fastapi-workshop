from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import ExpiredSignatureError, JWTError
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import (
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.security.jwt import decode_token, hash_token
from app.security.passwords import hash_password, verify_password
from app.security.tokens import issue_token_pair
from app.utils import utcnow

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _invalid_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a local account. The password is stored only as a bcrypt hash.",
    responses={409: {"description": "Username or email already exists"}},
)
def register(data: UserRegister, db: Session = Depends(get_db)):
    email = data.email.lower()

    existing = db.execute(
        select(User).where(or_(User.email == email, User.username == data.username))
    ).scalars().first()
    if existing is not None:
        field = "Email" if existing.email == email else "Username"
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{field} already registered")

    user = User(
        username=data.username,
        full_name=data.full_name,
        email=email,
        password_hash=hash_password(data.password),
        auth_provider="local",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # carrera entre dos registros simultaneos
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Username or email already registered")
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email and password",
    description=(
        "Returns a short-lived access token and a longer-lived refresh token. "
        "With `remember_me=true` the refresh token lasts 30 days instead of 7; "
        "the access token always keeps its short lifetime."
    ),
    responses={401: {"description": "Incorrect email or password"}},
)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == data.email.lower())).scalar_one_or_none()

    # Mismo mensaje si el correo no existe o la clave es incorrecta (no filtra que cuentas existen).
    # Las cuentas solo-sociales (password_hash NULL) tampoco pueden entrar por aqui.
    if user is None or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return issue_token_pair(db, user, data.remember_me)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Get a new access token using a refresh token",
    description=(
        "Verifies signature, expiration, token type, that the session exists and is not revoked, "
        "and that the user is still active. Uses **refresh-token rotation**: the used refresh "
        "token is revoked and a new one is returned."
    ),
    responses={401: {"description": "Invalid, expired or revoked refresh token"}},
)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    try:
        decode_token(data.refresh_token, expected_type="refresh")
    except (ExpiredSignatureError, JWTError):
        raise _invalid_refresh()

    stored = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(data.refresh_token))
    ).scalar_one_or_none()

    if stored is None or stored.revoked_at is not None or stored.expires_at <= utcnow():
        raise _invalid_refresh()

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise _invalid_refresh()

    # Rotacion: el token usado queda revocado y se emite uno nuevo (misma politica remember_me)
    stored.revoked_at = utcnow()
    return issue_token_pair(db, user, stored.remember_me)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out (revoke the refresh token)",
    description=(
        "Revokes the given refresh token/session in the database, so it can no longer be used "
        "to obtain new access tokens. Already-issued access tokens stay valid until they expire "
        "(15 minutes), because JWT access tokens are stateless."
    ),
    responses={401: {"description": "Malformed refresh token"}},
)
def logout(data: LogoutRequest, db: Session = Depends(get_db)):
    try:
        decode_token(data.refresh_token, expected_type="refresh", verify_exp=False)
    except JWTError:
        raise _invalid_refresh()

    stored = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(data.refresh_token))
    ).scalar_one_or_none()

    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = utcnow()
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
