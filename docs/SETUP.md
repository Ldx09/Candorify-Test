# Candorify Backend — Setup

## Requirements
- Python 3.11+

## Install
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# source .venv/bin/activate        # Mac/Linux
pip install -r requirements.txt
```

## Start the server
```bash
uvicorn server:app --reload --port 8000
```

## Verify
- http://127.0.0.1:8000/health → `{"status": "ok"}` (HTTP 200)
- http://127.0.0.1:8000/docs → interactive API docs

## Environment variables
Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | Example |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+psycopg://candorify:candorify@localhost:5432/candorify` |
| `JWT_SECRET` | yes | output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no (default 60) | `60` |

## Auth API
| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| POST | `/api/auth/signup` | `{email, password (8–72 chars), full_name?}` | 201 user | 409 email taken · 422 invalid input |
| POST | `/api/auth/login` | `{email, password}` | 200 `{access_token, token_type}` | 401 wrong email/password |
| GET | `/api/me` | header `Authorization: Bearer <token>` | 200 user | 401 not logged in / expired |

Every error returns `{"detail": "message to show the user"}`. Validation errors (422) also include `errors: [{field, message}]` for showing messages under each form field.

## env table
| `CORS_ORIGINS` | no (defaults to the Tauri origins) | `["http://localhost:1420","http://tauri.localhost"]` |