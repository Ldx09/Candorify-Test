"""Keeps a count of codes users looked up that we couldn't explain (see app/models/missing_code_record.py)."""
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.missing_code_record import MissingCodeRecord
from app.translation.service import OFFLINE_MESSAGE, CodeInfo

logger = logging.getLogger("candorify.missing_codes")


def record_missing(db: Session, info: CodeInfo) -> None:
    """Counts a code we had no answer for. Skips text that isn't a valid code shape and lookups that failed
    only because the code database was unreachable. Never breaks the lookup if saving fails."""
    if info.source != "not_found" or info.system == "unknown" or info.message is None:
        return
    if info.message == OFFLINE_MESSAGE:
        return
    try:
        rec = db.scalar(select(MissingCodeRecord).where(MissingCodeRecord.code == info.code,
                                                        MissingCodeRecord.system == info.system))
        if rec is None:
            db.add(MissingCodeRecord(code=info.code, system=info.system, times_asked=1))
        else:
            rec.times_asked += 1
            rec.last_asked = func.now()
        db.commit()
    except Exception as exc:  # e.g. two people logging the same new code at once
        db.rollback()
        logger.warning("Couldn't record missing code %s (%s)", info.code, exc.__class__.__name__)


def most_asked(db: Session, limit: int = 50) -> list[MissingCodeRecord]:
    return list(db.scalars(select(MissingCodeRecord)
                           .order_by(MissingCodeRecord.times_asked.desc(), MissingCodeRecord.last_asked.desc())
                           .limit(limit)))