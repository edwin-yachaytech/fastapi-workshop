"""Hash de contrasenas con bcrypt (directo, sin passlib).

Nota: passlib ya no se mantiene y falla con bcrypt >= 4.1, por eso usamos bcrypt.
"""
import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # p.ej. contrasena de mas de 72 bytes: nunca puede coincidir
        return False
