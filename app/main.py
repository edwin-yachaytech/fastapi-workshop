from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.config import SESSION_SECRET
from app.database import Base, engine
from app import models  # noqa: F401  (registra las tablas en Base.metadata)
from app.routers import auth, public, social, tasks, users

tags_metadata = [
    {"name": "Public", "description": "Endpoints that **do not** require authentication."},
    {"name": "Authentication", "description": "Register, log in (JWT), refresh tokens, log out. Supports *Remember Me*."},
    {"name": "Social Authentication", "description": "Sign in / sign up with GitHub (OAuth 2.0)."},
    {"name": "Users", "description": "Information about the authenticated user."},
    {"name": "Tasks", "description": "CRUD of tasks. **Protected by JWT**; each user only sees and edits their own tasks."},
]

app = FastAPI(
    title="FastAPI Workshop API",
    description=(
        "REST API developed for the Web Applications course.\n\n"
        "**How to authenticate in this page:** call `POST /auth/register`, then `POST /auth/login`, "
        "copy the `access_token`, click the **Authorize** button (top right) and paste it."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# Necesario para el flujo OAuth (guarda el parametro "state" entre redirect y callback)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

Base.metadata.create_all(bind=engine)

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(social.router)
app.include_router(users.router)
app.include_router(tasks.router)


@app.get("/", tags=["Public"], summary="API root")
def root():
    return {
        "message": "FastAPI Workshop API",
        "version": "1.0.0",
    }
