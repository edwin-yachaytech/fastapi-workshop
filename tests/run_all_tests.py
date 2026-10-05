"""Pruebas de la API (casos de la seccion 26 del enunciado).

Uso (con el servidor corriendo y el venv activo, desde la raiz del proyecto):
    python tests/run_all_tests.py

Los casos de login social, Swagger UI y Postman se prueban a mano (ver README).
"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv
from jose import jwt

load_dotenv()

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")
SECRET = os.getenv("JWT_SECRET", "")

stamp = str(int(time.time()))
USER = {
    "username": f"student{stamp}",
    "full_name": "Ana Torres",
    "email": f"ana{stamp}@example.com",
    "password": "MySecurePassword123!",
}
OTHER = {
    "username": f"other{stamp}",
    "full_name": "Otro Usuario",
    "email": f"otro{stamp}@example.com",
    "password": "AnotherPassword456!",
}

results: list[tuple[str, str, bool, str]] = []


def check(name: str, expected: str, ok: bool, detail: str = "") -> None:
    results.append((name, expected, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name:<42} expected: {expected:<22} {detail}")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def lifetime_seconds(token: str) -> int:
    claims = jwt.get_unverified_claims(token)
    return claims["exp"] - claims["iat"]


# ---------------------------------------------------------------- public
r = requests.get(f"{BASE}/public/info")
check("Public endpoint without JWT", "200 Success", r.status_code == 200, f"-> {r.status_code}")

# ---------------------------------------------------------------- registration
r = requests.post(f"{BASE}/auth/register", json=USER)
check("Registration with valid information", "201 User created", r.status_code == 201, f"-> {r.status_code}")
body = r.json() if r.ok else {}
check("  ...response never has password_hash", "no hash returned", "password_hash" not in body and "password" not in body)

r = requests.post(f"{BASE}/auth/register", json={**USER, "username": USER["username"] + "x"})
check("Duplicate email", "409 Rejected", r.status_code == 409, f"-> {r.status_code}")

r = requests.post(f"{BASE}/auth/register", json={**USER, "username": "bademail1", "email": "not-an-email"})
check("Invalid email", "422 Rejected", r.status_code == 422, f"-> {r.status_code}")

requests.post(f"{BASE}/auth/register", json=OTHER)

# ---------------------------------------------------------------- login
r = requests.post(f"{BASE}/auth/login", json={"email": USER["email"], "password": USER["password"]})
tokens = r.json() if r.ok else {}
check("Login with correct password", "200 Tokens returned",
      r.status_code == 200 and "access_token" in tokens and "refresh_token" in tokens, f"-> {r.status_code}")
ACCESS, REFRESH = tokens.get("access_token", ""), tokens.get("refresh_token", "")

r = requests.post(f"{BASE}/auth/login", json={"email": USER["email"], "password": "WrongPassword!"})
check("Login with incorrect password", "401", r.status_code == 401, f"-> {r.status_code}")

# ---------------------------------------------------------------- /users/me
r = requests.get(f"{BASE}/users/me")
check("/users/me without token", "401 Rejected", r.status_code == 401, f"-> {r.status_code}")

r = requests.get(f"{BASE}/users/me", headers=auth(ACCESS))
me = r.json() if r.ok else {}
check("/users/me with valid token", "200 User returned",
      r.status_code == 200 and me.get("email") == USER["email"] and "password_hash" not in me, f"-> {r.status_code}")

# ---------------------------------------------------------------- protected CRUD
r = requests.get(f"{BASE}/tasks")
check("Protected CRUD without JWT", "401 Rejected", r.status_code == 401, f"-> {r.status_code}")

r = requests.post(f"{BASE}/tasks", json={"title": "Prepare FastAPI workshop", "description": "JWT + Swagger"}, headers=auth(ACCESS))
task = r.json() if r.status_code == 201 else {}
check("Protected CRUD with JWT (create)", "201 Success", r.status_code == 201, f"-> {r.status_code}")
TASK_ID = task.get("id")

# user_id enviado por el cliente debe ser ignorado (el dueno sale del JWT)
r = requests.post(f"{BASE}/tasks", json={"title": "Try to spoof owner", "user_id": 999999}, headers=auth(ACCESS))
check("  ...client-supplied user_id is ignored", "owner = me", r.status_code == 201 and r.json().get("user_id") == me.get("id"))

r = requests.get(f"{BASE}/tasks", headers=auth(ACCESS))
check("Protected CRUD with JWT (list)", "200 Success", r.status_code == 200 and len(r.json()) >= 1, f"-> {r.status_code}")
r = requests.get(f"{BASE}/tasks/{TASK_ID}", headers=auth(ACCESS))
check("Protected CRUD with JWT (get one)", "200 Success", r.status_code == 200, f"-> {r.status_code}")
r = requests.put(f"{BASE}/tasks/{TASK_ID}", json={"title": "Prepare FastAPI workshop", "status": "in_progress"}, headers=auth(ACCESS))
check("Protected CRUD with JWT (PUT)", "200 Success", r.status_code == 200 and r.json()["status"] == "in_progress", f"-> {r.status_code}")
r = requests.patch(f"{BASE}/tasks/{TASK_ID}", json={"status": "done"}, headers=auth(ACCESS))
check("Protected CRUD with JWT (PATCH)", "200 Success", r.status_code == 200 and r.json()["status"] == "done", f"-> {r.status_code}")

# ---------------------------------------------------------------- authorization (otro usuario)
r = requests.post(f"{BASE}/auth/login", json={"email": OTHER["email"], "password": OTHER["password"]})
OTHER_ACCESS = r.json().get("access_token", "")
r = requests.get(f"{BASE}/tasks/{TASK_ID}", headers=auth(OTHER_ACCESS))
check("Access another user's protected resource", "403 Rejected", r.status_code == 403, f"-> {r.status_code}")
r = requests.delete(f"{BASE}/tasks/{TASK_ID}", headers=auth(OTHER_ACCESS))
check("  ...delete another user's task", "403 Rejected", r.status_code == 403, f"-> {r.status_code}")

# ---------------------------------------------------------------- invalid / expired token
r = requests.get(f"{BASE}/users/me", headers=auth("this.is.not-a-jwt"))
check("Invalid token", "401 Rejected", r.status_code == 401, f"-> {r.status_code}")

if SECRET:
    expired = jwt.encode(
        {"sub": str(me.get("id")), "type": "access", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET, algorithm="HS256",
    )
    r = requests.get(f"{BASE}/users/me", headers=auth(expired))
    check("Expired token", "401 Rejected", r.status_code == 401, f"-> {r.status_code} {r.json().get('detail')}")

# un refresh token no debe servir como access token
r = requests.get(f"{BASE}/users/me", headers=auth(REFRESH))
check("Refresh token used as access token", "401 Rejected", r.status_code == 401, f"-> {r.status_code}")

# ---------------------------------------------------------------- refresh
r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": REFRESH})
new = r.json() if r.ok else {}
check("Refresh valid token", "200 New token issued", r.status_code == 200 and "access_token" in new, f"-> {r.status_code}")
NEW_REFRESH = new.get("refresh_token", "")

r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": "garbage"})
check("Invalid refresh token", "401 Rejected", r.status_code == 401, f"-> {r.status_code}")

r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": ACCESS})
check("Access token used as refresh token", "401 Rejected", r.status_code == 401, f"-> {r.status_code}")

r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": REFRESH})
check("Rotated (already used) refresh token", "401 Rejected", r.status_code == 401, f"-> {r.status_code}")

# ---------------------------------------------------------------- logout
r = requests.post(f"{BASE}/auth/logout", json={"refresh_token": NEW_REFRESH})
check("Logout", "204 Session revoked", r.status_code == 204, f"-> {r.status_code}")
r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": NEW_REFRESH})
check("Use revoked refresh token", "401 Rejected", r.status_code == 401, f"-> {r.status_code}")

# ---------------------------------------------------------------- remember me
r1 = requests.post(f"{BASE}/auth/login", json={"email": USER["email"], "password": USER["password"], "remember_me": False}).json()
r2 = requests.post(f"{BASE}/auth/login", json={"email": USER["email"], "password": USER["password"], "remember_me": True}).json()
d_false = round(lifetime_seconds(r1["refresh_token"]) / 86400, 2)
d_true = round(lifetime_seconds(r2["refresh_token"]) / 86400, 2)
check("Remember Me = false", "refresh ~7 days", abs(d_false - 7) < 0.1, f"-> {d_false} days")
check("Remember Me = true", "refresh ~30 days", abs(d_true - 30) < 0.1, f"-> {d_true} days")
a_false, a_true = lifetime_seconds(r1["access_token"]), lifetime_seconds(r2["access_token"])
check("  ...access token stays short (both)", "15 minutes", a_false == a_true == 15 * 60,
      f"-> {a_false // 60} min / {a_true // 60} min")

# ---------------------------------------------------------------- cleanup: delete
r = requests.delete(f"{BASE}/tasks/{TASK_ID}", headers=auth(ACCESS))
check("Protected CRUD with JWT (delete)", "204 Success", r.status_code == 204, f"-> {r.status_code}")
r = requests.get(f"{BASE}/tasks/{TASK_ID}", headers=auth(ACCESS))
check("  ...deleted task is gone", "404", r.status_code == 404, f"-> {r.status_code}")

# ---------------------------------------------------------------- resumen
passed = sum(1 for _, _, ok, _ in results if ok)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
