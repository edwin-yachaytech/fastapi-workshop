# FastAPI Workshop API

REST API built for the *Web Applications* course (Workshop 5): FastAPI + SQLAlchemy + MySQL,
JWT authentication (access + refresh tokens, logout, Remember Me), GitHub social login,
a JWT-protected CRUD (`Task`), automatic OpenAPI docs, and Postman/Swagger testing.

**Author:** Edwin Fabricio Quizhpe Aguilar

## Project structure

```
fastapi-workshop/
├── app/
│   ├── main.py            # FastAPI app, tags, middleware, routers
│   ├── config.py          # reads secrets from .env
│   ├── database.py        # SQLAlchemy engine / session
│   ├── models/            # User, Task, RefreshToken
│   ├── schemas/           # Pydantic request/response models
│   ├── routers/           # public, auth, social, users, tasks
│   └── security/          # jwt.py, passwords.py, tokens.py, dependencies.py
├── tests/run_all_tests.py # automated checks for the required test table
├── postman/               # Postman collection (with automatic tests)
├── .env.example           # copy to .env (never commit .env)
└── requirements.txt
```

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit the values
uvicorn app.main:app --reload
```

Generate a strong secret for `JWT_SECRET`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Create the MySQL database and user once:

```sql
CREATE DATABASE workshop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'apiuser'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON workshop.* TO 'apiuser'@'localhost';
FLUSH PRIVILEGES;
```

Tables are created automatically on startup. Documentation: <http://127.0.0.1:8000/docs>

## Endpoints

| Group | Method | Path | Auth |
|---|---|---|---|
| Public | GET | `/`, `/public/info`, `/public/task-statuses` | no |
| Authentication | POST | `/auth/register` | no |
| Authentication | POST | `/auth/login` (`remember_me`) | no |
| Authentication | POST | `/auth/refresh` (rotation) | refresh token in body |
| Authentication | POST | `/auth/logout` (revokes session) | refresh token in body |
| Social | GET | `/auth/github/login`, `/auth/github/callback` | no |
| Users | GET | `/users/me` | Bearer JWT |
| Tasks | POST / GET | `/tasks` | Bearer JWT |
| Tasks | GET / PUT / PATCH / DELETE | `/tasks/{id}` | Bearer JWT + ownership |

## Design decisions

* **Access token** 15 min; **refresh token** 7 days, or 30 days with `remember_me=true`
  (Remember Me never lengthens the access token).
* Refresh tokens are stored **hashed (SHA-256)** in `refresh_tokens`; logout sets `revoked_at`.
  Refresh uses **rotation**: the used token is revoked and a new one is issued.
* Passwords are hashed with **bcrypt**; the hash is never returned by the API.
* The task owner comes from the **JWT**, never from a `user_id` sent by the client.
  Accessing another user's task returns **403**.
* Correct status codes: 201, 204, 401, 403, 404, 409, 422.
* Social accounts have `password_hash = NULL` and cannot use `/auth/login`.

## Tests

With the server running:

```bash
python tests/run_all_tests.py        # automated checks (all expected to PASS)
```

Import `postman/FastAPI_Workshop.postman_collection.json` into Postman and run it with the
Collection Runner; every request has automatic tests.

## GitHub login setup

1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.
2. Homepage URL: `http://127.0.0.1:8000` — Authorization callback URL:
   `http://127.0.0.1:8000/auth/github/callback`.
3. Put the Client ID / Client Secret in `.env`, restart the server and open
   <http://127.0.0.1:8000/auth/github/login> in the browser (use `127.0.0.1`, not `localhost`).
