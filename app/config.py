"""Configuracion central: todo secreto se lee desde variables de entorno (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno {name}. Revisa tu archivo .env"
        )
    return value


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://apiuser:password@localhost/workshop",
)

JWT_SECRET = _required("JWT_SECRET")
JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
REMEMBER_REFRESH_TOKEN_DAYS = int(os.getenv("REMEMBER_REFRESH_TOKEN_DAYS", "30"))

# Necesario para el flujo OAuth (guarda el "state" entre el redirect y el callback)
SESSION_SECRET = os.getenv("SESSION_SECRET", JWT_SECRET)

# Login social con GitHub (opcional: si no se configura, esos endpoints responden 503)
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv(
    "GITHUB_REDIRECT_URI",
    "http://127.0.0.1:8000/auth/github/callback",
)
