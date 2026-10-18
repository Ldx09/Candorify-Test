# Candorify Backend — Setup

## Run locally
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env               # then fill in DATABASE_URL and JWT_SECRET
uvicorn server:app --reload --port 8000
```
Check: http://127.0.0.1:8000/health → `{"status": "ok"}` · API docs: http://127.0.0.1:8000/docs

## Environment variables
| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | – | `postgresql+psycopg://user:pass@host:5432/candorify`. `postgres://` URLs from hosts are converted automatically. SQLite (`sqlite:///./dev.db`) is for local testing only. |
| `JWT_SECRET` | yes | – | Random string: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. At least 32 characters in production. Never commit it. |
| `ENV` | no | `development` | Set `production` on the host. This turns on HTTPS redirect + HSTS, hides `/docs`, and refuses weak settings (short secret, SQLite, CORS `*`). |
| `CORS_ORIGINS` | no | Tauri origins | JSON list of allowed frontend origins, e.g. `["https://candorify.app","http://tauri.localhost"]`. Never `*`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `60` | Login token lifetime. |
| `RETENTION_DAYS` | no | `30` | Bills are deleted automatically this many days after upload. |
| `RETENTION_SWEEP_MINUTES` | no | `60` | How often the automatic sweep runs (`0` = off; run `python -m scripts.retention_sweep` instead). |
| `DOCS_ENABLED` | no | on in dev, off in prod | Force `/docs` on or off. |

## Data deletion & retention
- `DELETE /api/me`: one-tap deletion of the account, all bills and all bill lines (no orphaned rows).
- `DELETE /api/bills/{id}`: deletes one bill and its lines.
- Retention sweep: runs at startup and every `RETENTION_SWEEP_MINUTES`, and deletes only bills older than `RETENTION_DAYS`. Accounts and newer bills are never touched. `GET /api/bills` shows each bill's `expires_at`.

## Security
- HTTPS in transit: the host provides TLS; in production, plain-HTTP requests get a 308 redirect to HTTPS, plus HSTS.
- Security headers on every response: `nosniff`, `X-Frame-Options: DENY`, `no-referrer`, `Cache-Control: no-store`.
- No secrets in responses or logs: password hashes are never returned, unexpected errors return a generic message, and the DB password is masked in logs.
- CORS is limited to `CORS_ORIGINS`. Every `/api/*` route except signup/login requires a valid token.

## Deploy (Render)
1. Push this repo to GitHub (it can be private). `render.yaml` is in the repo root.
2. Render → **New → Blueprint** → pick the repo → **Apply**. This creates the web service and a PostgreSQL database, and generates `JWT_SECRET`.
3. Wait for the deploy, then open `https://<service>.onrender.com/health` → `{"status":"ok"}`.
4. Run the demo check: `python -m scripts.demo_smoke https://<service>.onrender.com`

## Midterm demo path
health → sign up → log in → `POST /api/bills/sample {"sample_id":"BILL-001"}` → `POST /api/bills/{id}/check`
→ `GET /api/bills/{id}/translate` → `POST /api/letters {"bill_id":…, "letter_type":"dispute"}`

`python -m scripts.demo_smoke <url>` runs this whole path and prints PASS/FAIL for each step.