"""Data deletion and retention.

- delete_bills(): removes bills AND their lines, flags and answers explicitly, so no orphaned rows are left behind
  (we don't rely only on the database's ON DELETE CASCADE).
- delete_user_and_data(): one-tap account deletion: flags + answers + lines -> bills -> user, in one transaction.
- sweep_expired_bills(): deletes bills older than RETENTION_DAYS. It touches nothing else:
  users and newer bills are never deleted.
"""
import logging
import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import IS_SQLITE, SessionLocal
from app.models.answer_record import AnswerRecord
from app.models.bill_record import BillLineRecord, BillRecord
from app.models.flag_record import FlagRecord
from app.models.user import User

logger = logging.getLogger("candorify.retention")


def delete_bills(db: Session, bill_ids: list[int]) -> int:
    """Deletes the given bills with all their lines, flags and answers. Caller commits."""
    if not bill_ids:
        return 0
    db.execute(delete(FlagRecord).where(FlagRecord.bill_id.in_(bill_ids)))
    db.execute(delete(AnswerRecord).where(AnswerRecord.bill_id.in_(bill_ids)))
    db.execute(delete(BillLineRecord).where(BillLineRecord.bill_id.in_(bill_ids)))
    result = db.execute(delete(BillRecord).where(BillRecord.id.in_(bill_ids)))
    return result.rowcount


def delete_user_and_data(db: Session, user: User) -> int:
    """Deletes the user's bill lines, bills and account in one transaction. Returns bills deleted."""
    bill_ids = list(db.scalars(select(BillRecord.id).where(BillRecord.user_id == user.id)))
    try:
        count = delete_bills(db, bill_ids)
        db.execute(delete(User).where(User.id == user.id))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return count


def retention_cutoff(now: datetime | None = None) -> datetime:
    """Bills created before this moment are expired."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings.RETENTION_DAYS)
    # SQLite stores timestamps as naive UTC text; Postgres compares timezone-aware values.
    return cutoff.replace(tzinfo=None) if IS_SQLITE else cutoff


def sweep_expired_bills(db: Session, now: datetime | None = None) -> int:
    """Deletes every bill older than RETENTION_DAYS (and its lines). Nothing else is touched."""
    cutoff = retention_cutoff(now)
    expired = list(db.scalars(select(BillRecord.id).where(BillRecord.created_at < cutoff)))
    try:
        count = delete_bills(db, expired)
        db.commit()
    except Exception:
        db.rollback()
        raise
    if count:
        logger.info("Retention sweep deleted %d expired bill(s)", count)
    return count


def run_sweep_once() -> int:
    with SessionLocal() as db:
        return sweep_expired_bills(db)


class RetentionScheduler:
    """Runs the sweep at startup and then every RETENTION_SWEEP_MINUTES in a background thread."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if settings.RETENTION_SWEEP_MINUTES <= 0:
            return
        self._thread = threading.Thread(target=self._loop, name="retention-sweep", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                run_sweep_once()
            except Exception as exc:  # never crash the app because of the sweep; try again next time
                logger.error("Retention sweep failed: %s", exc.__class__.__name__)
            self._stop.wait(settings.RETENTION_SWEEP_MINUTES * 60)