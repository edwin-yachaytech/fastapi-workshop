"""Registro / login con GitHub (OAuth 2.0).

Flujo:
  Browser -> GET /auth/github/login -> redirect a GitHub (login + consentimiento)
  GitHub  -> GET /auth/github/callback?code=...  -> FastAPI verifica, busca/crea el usuario local
  y entrega los JWT de la propia aplicacion.

La contrasena de GitHub NUNCA pasa por nuestra API.
"""
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_REDIRECT_URI
from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenResponse
from app.security.tokens import issue_token_pair

router = APIRouter(prefix="/auth/github", tags=["Social Authentication"])

oauth = OAuth()
oauth.register(
    name="github",
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)


def _require_configured() -> None:
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub login is not configured (set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env)",
        )


@router.get(
    "/login",
    summary="Start the GitHub login flow",
    description=(
        "Redirects the browser to GitHub. Open this URL **in a browser tab** "
        "(Swagger's 'Try it out' cannot follow the redirect to GitHub)."
    ),
    responses={302: {"description": "Redirect to GitHub"}, 503: {"description": "GitHub login not configured"}},
)
async def github_login(request: Request):
    _require_configured()
    return await oauth.github.authorize_redirect(request, GITHUB_REDIRECT_URI)


@router.get(
    "/callback",
    response_model=TokenResponse,
    summary="GitHub OAuth callback",
    description=(
        "GitHub redirects here after the user authorizes the app. The API exchanges the code, "
        "reads the GitHub identity, finds or creates the local user and returns the application's own JWTs."
    ),
    responses={400: {"description": "OAuth error"}, 409: {"description": "Email already used by another account"}},
)
async def github_callback(request: Request, db: Session = Depends(get_db)):
    _require_configured()

    try:
        token = await oauth.github.authorize_access_token(request)
    except OAuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"OAuth error: {exc.error}")

    profile = (await oauth.github.get("user", token=token)).json()
    github_id = str(profile["id"])
    login = profile["login"]
    email = profile.get("email")

    # El correo puede ser privado: lo pedimos aparte y usamos solo uno verificado
    if not email:
        emails = (await oauth.github.get("user/emails", token=token)).json()
        verified = [e for e in emails if e.get("verified")]
        primary = next((e for e in verified if e.get("primary")), None)
        chosen = primary or (verified[0] if verified else None)
        if chosen is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="GitHub account has no verified email")
        email = chosen["email"]
    email = email.lower()

    # 1) Buscar por identidad del proveedor
    user = db.execute(
        select(User).where(User.auth_provider == "github", User.provider_user_id == github_id)
    ).scalar_one_or_none()

    # 2) Si no existe, crear
    if user is None:
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none() is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="This email is already registered with another sign-in method",
            )
        username = login
        if db.execute(select(User).where(User.username == username)).scalar_one_or_none() is not None:
            username = f"{login}-{github_id}"[:50]

        user = User(
            username=username,
            full_name=profile.get("name") or login,
            email=email,
            password_hash=None,  # cuenta solo social
            auth_provider="github",
            provider_user_id=github_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return issue_token_pair(db, user, remember_me=False)
