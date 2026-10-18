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
None required yet. The port is set by the `--port` flag in the start command (default 8000).
New variables will be listed here as features are added.