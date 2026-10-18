"""Saves the check engine's flags for a stored bill so each flag has an id and a user-controlled status.

The engine decides WHICH flags exist (deterministic, no AI). Re-checking a bill keeps the status the
user already chose for a flag that is still found, adds new flags as "investigating", and removes
flags the engine no longer finds. Flags created from the patient's answers (answer_mismatch) are managed
by app/services/answers.py and are never touched here.
"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.checks import run_checks
from app.engine.models import ENGINE_RULES, Flag, FlagReport
from app.models.bill_record import BillRecord
from app.models.flag_record import DEFAULT_STATUS, FlagRecord


def _sort_key(f: Flag):
    return (f.line_no is None, f.line_no or 0, f.rule)


def sync_flags(db: Session, bill: BillRecord) -> FlagReport:
    """Runs the engine on the bill, saves the result, and returns the flags with ids and statuses."""
    found = run_checks(bill.to_engine_bill()).flags
    existing = {(r.rule, r.line_no): r for r in db.scalars(
        select(FlagRecord).where(FlagRecord.bill_id == bill.id, FlagRecord.rule.in_(ENGINE_RULES)))}
    keep: set[tuple] = set()
    for f in found:
        key = (f.rule, f.line_no)
        keep.add(key)
        rec = existing.get(key)
        if rec is None:
            rec = FlagRecord(bill_id=bill.id, rule=f.rule, line_no=f.line_no, status=DEFAULT_STATUS)
            db.add(rec)
        rec.code, rec.message, rec.expected, rec.actual = f.code, f.message, f.expected, f.actual
        rec.related_line_no, rec.line_numbers = f.related_line_no, json.dumps(f.line_numbers)
    for key, rec in existing.items():
        if key not in keep:
            db.delete(rec)
    db.commit()
    return all_flags(db, bill)


def all_flags(db: Session, bill: BillRecord) -> FlagReport:
    """Every saved flag on the bill (engine + answer flags), sorted by line."""
    flags = sorted((r.to_flag() for r in db.scalars(select(FlagRecord).where(FlagRecord.bill_id == bill.id))),
                   key=_sort_key)
    return FlagReport(bill_id=str(bill.id), flag_count=len(flags), flags=flags)


def stored_flags(db: Session, bill: BillRecord) -> list[Flag]:
    """The bill's flags, making sure they are up to date with the engine first."""
    return sync_flags(db, bill).flags