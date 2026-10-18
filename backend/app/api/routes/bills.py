"""Bill endpoints. All are protected (mounted on the `protected` router in server.py),
and a user can only ever see, check or delete their own bills."""
import random
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.engine.loader import load_bills
from app.engine.models import Flag, FlagReport
from app.models.bill import Bill
from app.models.bill_record import BillLineRecord, BillRecord
from app.models.flag_record import FlagRecord
from app.models.user import User
from app.questions.localize import localize_questions
from app.schemas.bills import (BillIn, BillOut, BillSummary, FlagStatusUpdate, SampleBillRequest,
                               TranslatedBillOut, TranslatedLineOut)
from app.schemas.questions import QuestionsOut
from app.services.answers import bill_questions, saved_answers
from app.services.flags import sync_flags
from app.services.retention import delete_bills
from app.translation.languages import get_language
from app.translation.service import lookup_code
from app.translation.translator import translate_texts

router = APIRouter(prefix="/bills", tags=["bills"])

NOT_FOUND = "Bill not found"
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
SAMPLE_BILLS_FILES = (DATA_DIR / "synthetic_bills.csv", DATA_DIR / "demo_bills.csv")


def get_own_bill(db: Session, bill_id: int, user: User) -> BillRecord:
    """Returns the bill if it belongs to this user. Someone else's bill gets the same 404 as a
    missing one, so bill ids can't be probed."""
    bill = db.get(BillRecord, bill_id)
    if bill is None or bill.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return bill


def save_bill(db: Session, user: User, bill: Bill, label: str | None) -> BillRecord:
    record = BillRecord(user_id=user.id, label=label, stated_subtotal=bill.stated_subtotal,
                        date_of_service=bill.date_of_service)
    record.lines = [BillLineRecord(line_no=i, code=ln.code, description=ln.description, quantity=ln.quantity,
                                   unit_price=ln.unit_price, line_total=ln.line_total)
                    for i, ln in enumerate(bill.lines, start=1)]
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@lru_cache(maxsize=1)
def _sample_bills() -> dict[str, Bill]:
    return {b.bill_id.upper(): b for f in SAMPLE_BILLS_FILES for b in load_bills(f)}


def make_sample_bill(body: SampleBillRequest) -> tuple[Bill, str]:
    """The provided sample bill (sample_id) or a freshly generated one. Returns (bill, label)."""
    if body.sample_id:
        bill = _sample_bills().get(body.sample_id.strip().upper())
        if bill is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                                f"No sample bill '{body.sample_id}'. Use BILL-001 to BILL-020 or DEMO-001 to DEMO-004.")
        return bill, bill.bill_id

    from scripts.generate_bills import DEFECT_TYPES, generate_bill  # deterministic generator, no AI
    rng = random.Random()
    defect = body.defect or rng.choice(DEFECT_TYPES)
    lines, stated_subtotal, _key = generate_bill(rng, "GEN", defect, vary_wording=True)
    bill = Bill(bill_id="GEN", stated_subtotal=stated_subtotal, lines=[
        dict(line_no=ln["line_no"], code=ln["code"], description=ln["description"], quantity=ln["quantity"],
             unit_price=ln["unit_price"], line_total=ln["line_total"]) for ln in lines])
    return bill, "Generated sample bill"


@router.get("", response_model=list[BillSummary])
def list_bills(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The user's bills, newest first."""
    rows = db.execute(
        select(BillRecord, func.count(BillLineRecord.id))
        .outerjoin(BillLineRecord, BillLineRecord.bill_id == BillRecord.id)
        .where(BillRecord.user_id == user.id)
        .group_by(BillRecord.id)
        .order_by(BillRecord.created_at.desc(), BillRecord.id.desc())
    ).all()
    keep = timedelta(days=settings.RETENTION_DAYS)
    return [BillSummary(id=b.id, label=b.label, stated_subtotal=b.stated_subtotal, line_count=n,
                        created_at=b.created_at, expires_at=b.created_at + keep) for b, n in rows]


@router.post("", response_model=BillOut, status_code=status.HTTP_201_CREATED)
def create_bill(body: BillIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Stores a bill for the logged-in user. Lines are numbered 1, 2, 3... in the order sent."""
    bill = BillRecord(user_id=user.id, label=body.label, stated_subtotal=body.stated_subtotal,
                      date_of_service=body.date_of_service)
    bill.lines = [BillLineRecord(line_no=i, **line.model_dump()) for i, line in enumerate(body.lines, start=1)]
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


@router.post("/sample", response_model=BillOut, status_code=status.HTTP_201_CREATED)
def create_sample_bill(body: SampleBillRequest | None = None, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Demo helper: stores a sample bill for the logged-in user in one call (bill only; use
    POST /api/upload/sample to also get the flags and follow-up questions)."""
    bill, label = make_sample_bill(body or SampleBillRequest())
    return save_bill(db, user, bill, label)


@router.patch("/flags/{flag_id}", response_model=Flag)
def update_flag_status(flag_id: int, body: FlagStatusUpdate, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Sets a flag's status: "investigating", "add_to_letter" (goes in the dispute letter) or
    "dismissed" (the user says this charge is fine)."""
    flag = db.get(FlagRecord, flag_id)
    bill = db.get(BillRecord, flag.bill_id) if flag else None
    if flag is None or bill is None or bill.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flag not found")
    flag.status = body.status
    db.commit()
    db.refresh(flag)
    return flag.to_flag()


@router.get("/{bill_id}", response_model=BillOut)
def get_bill(bill_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_own_bill(db, bill_id, user)


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(bill_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Permanently deletes one bill and all its lines."""
    bill = get_own_bill(db, bill_id, user)
    delete_bills(db, [bill.id])
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{bill_id}/check", response_model=FlagReport)
def check_bill(bill_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Runs the deterministic check engine on the bill and returns the flag report.
    Every flag has an `id` and a `status` (new flags start as "investigating"). Running it again keeps
    the status the user already chose for flags that are still found."""
    bill = get_own_bill(db, bill_id, user)
    return sync_flags(db, bill)


@router.get("/{bill_id}/questions", response_model=QuestionsOut)
def get_questions(bill_id: int, language: str | None = Query(default=None, max_length=10,
                                                             description="Optional, e.g. es, ar, zh"),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The bill's follow-up questions (max 5), in the user's language, plus any answers already saved."""
    check_language(language)
    bill = get_own_bill(db, bill_id, user)
    loc = localize_questions(bill_questions(bill), language)
    return QuestionsOut(bill_id=bill.id, questions=loc.questions, answers=saved_answers(db, bill),
                        language=loc.language, rtl=loc.rtl, translation_note=loc.note)


def check_language(language: str | None) -> None:
    if language is not None and get_language(language) is None:
        raise HTTPException(422, f"Unsupported language '{language}'. See GET /api/languages for the list")


@router.get("/{bill_id}/translate", response_model=TranslatedBillOut)
def translate_bill(bill_id: int, language: str | None = Query(default=None, max_length=10,
                                                              description="Optional, e.g. es, ar, zh"),
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every line of the bill with its code explained in plain English, and optionally also in the
    user's language (`plain_english_translated`)."""
    check_language(language)
    bill = get_own_bill(db, bill_id, user)
    codes = {c: lookup_code(c) for c in {ln.code for ln in bill.lines}}
    lines = [TranslatedLineOut.model_validate(ln, from_attributes=True).model_copy(update={"code_info": codes[ln.code]})
             for ln in bill.lines]
    out = TranslatedBillOut(id=bill.id, label=bill.label, stated_subtotal=bill.stated_subtotal, lines=lines)
    if language:
        plain = sorted({ci.plain_english for ci in codes.values() if ci.plain_english})
        result = translate_texts(plain, language)
        by_source = {it.source: it.text for it in result.items if it.translated}
        for ln in out.lines:
            if ln.code_info and ln.code_info.plain_english in by_source:
                ln.plain_english_translated = by_source[ln.code_info.plain_english]
        out.language, out.rtl, out.translation_note = result.language.code, result.language.rtl, result.note
    return out