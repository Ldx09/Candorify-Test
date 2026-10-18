"""Bill endpoints. All are protected (mounted on the `protected` router in server.py),
and a user can only ever see, check or delete their own bills."""
import random
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.engine.checks import run_checks
from app.engine.loader import load_bills
from app.engine.models import FlagReport
from app.models.bill import Bill
from app.models.bill_record import BillLineRecord, BillRecord
from app.models.user import User
from app.schemas.bills import (BillIn, BillOut, BillSummary, SampleBillRequest, TranslatedBillOut,
                               TranslatedLineOut)
from app.services.retention import delete_bills
from app.translation.service import lookup_code

router = APIRouter(prefix="/bills", tags=["bills"])

NOT_FOUND = "Bill not found"
SAMPLE_BILLS_FILE = Path(__file__).resolve().parents[3] / "data" / "synthetic_bills.csv"


def get_own_bill(db: Session, bill_id: int, user: User) -> BillRecord:
    """Returns the bill if it belongs to this user. Someone else's bill gets the same 404 as a
    missing one, so bill ids can't be probed."""
    bill = db.get(BillRecord, bill_id)
    if bill is None or bill.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return bill


def _save(db: Session, user: User, bill: Bill, label: str | None) -> BillRecord:
    record = BillRecord(user_id=user.id, label=label, stated_subtotal=bill.stated_subtotal)
    record.lines = [BillLineRecord(line_no=i, code=ln.code, description=ln.description, quantity=ln.quantity,
                                   unit_price=ln.unit_price, line_total=ln.line_total)
                    for i, ln in enumerate(bill.lines, start=1)]
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@lru_cache(maxsize=1)
def _sample_bills() -> dict[str, Bill]:
    return {b.bill_id.upper(): b for b in load_bills(SAMPLE_BILLS_FILE)}


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
    bill = BillRecord(user_id=user.id, label=body.label, stated_subtotal=body.stated_subtotal)
    bill.lines = [BillLineRecord(line_no=i, **line.model_dump()) for i, line in enumerate(body.lines, start=1)]
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


@router.post("/sample", response_model=BillOut, status_code=status.HTTP_201_CREATED)
def create_sample_bill(body: SampleBillRequest | None = None, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Demo helper: stores a synthetic bill for the logged-in user in one call."""
    body = body or SampleBillRequest()
    if body.sample_id:
        bill = _sample_bills().get(body.sample_id.strip().upper())
        if bill is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                                f"No sample bill '{body.sample_id}'. Use BILL-001 to BILL-020.")
        return _save(db, user, bill, label=bill.bill_id)

    from scripts.generate_bills import DEFECT_TYPES, generate_bill  # deterministic generator, no AI
    rng = random.Random()
    defect = body.defect or rng.choice(DEFECT_TYPES)
    lines, stated_subtotal, _key = generate_bill(rng, "GEN", defect, vary_wording=True)
    bill = Bill(bill_id="GEN", stated_subtotal=stated_subtotal, lines=[
        dict(line_no=ln["line_no"], code=ln["code"], description=ln["description"], quantity=ln["quantity"],
             unit_price=ln["unit_price"], line_total=ln["line_total"]) for ln in lines])
    return _save(db, user, bill, label="Generated sample bill")


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
    """Runs the deterministic check engine on the bill and returns the flag report."""
    bill = get_own_bill(db, bill_id, user)
    return run_checks(bill.to_engine_bill())


@router.get("/{bill_id}/translate", response_model=TranslatedBillOut)
def translate_bill(bill_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every line of the bill with its code explained in plain English."""
    bill = get_own_bill(db, bill_id, user)
    codes = {c: lookup_code(c) for c in {ln.code for ln in bill.lines}}
    return TranslatedBillOut(
        id=bill.id, label=bill.label, stated_subtotal=bill.stated_subtotal,
        lines=[TranslatedLineOut.model_validate(ln, from_attributes=True).model_copy(update={"code_info": codes[ln.code]})
               for ln in bill.lines],
    )