"""Runs the retention sweep once (e.g. from a scheduled job on the host).

Run from the backend folder:   python -m scripts.retention_sweep
"""
from app.core.config import settings
from app.services.retention import run_sweep_once

if __name__ == "__main__":
    deleted = run_sweep_once()
    print(f"Deleted {deleted} bill(s) older than {settings.RETENTION_DAYS} days")