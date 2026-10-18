"""Bill endpoints. All are protected (mounted on the `protected` router in server.py),
and a user can only ever see or check their own bills."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.engine.checks import run_checks
from app.engine.models import FlagReport
from app.models.bill_record import BillLineRecord, BillRecord
from app.models.user import User
from app.letters.generator import LetterDetails, dispute_letter, request_letter
from app.schemas.bills import BillIn, BillOut, TranslatedBillOut, TranslatedLineOut
from app.schemas.letters import DisputeLetterRequest, LetterOut
from app.translation.lookup import lookup_code

router = APIRouter(prefix="/bills", tags=["bills"])

NOT_FOUND = "Bill not found"


def _get_own_bill(db: Session, bill_id: int, user: User) -> BillRecord:
    bill = db.get(BillRecord, bill_id)
    # Someone else's bill gets the same 404 as a missing one, so ids can't be probed.
    if bill is None or bill.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return bill


@router.post("", response_model=BillOut, status_code=status.HTTP_201_CREATED)
def create_bill(body: BillIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Stores a bill for the logged-in user. Lines are numbered 1, 2, 3... in the order sent."""
    bill = BillRecord(user_id=user.id, label=body.label, stated_subtotal=body.stated_subtotal)
    bill.lines = [BillLineRecord(line_no=i, **line.model_dump()) for i, line in enumerate(body.lines, start=1)]
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


@router.get("/{bill_id}", response_model=BillOut)
def get_bill(bill_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_own_bill(db, bill_id, user)


@router.post("/{bill_id}/check", response_model=FlagReport)
def check_bill(bill_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Runs the deterministic check engine on the bill and returns the flag report."""
    bill = _get_own_bill(db, bill_id, user)
    return run_checks(bill.to_engine_bill())


@router.get("/{bill_id}/translate", response_model=TranslatedBillOut)
def translate_bill(bill_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every line of the bill with its code explained in plain English."""
    bill = _get_own_bill(db, bill_id, user)
    codes = {c: lookup_code(c) for c in {ln.code for ln in bill.lines}}
    return TranslatedBillOut(
        id=bill.id, label=bill.label, stated_subtotal=bill.stated_subtotal,
        lines=[TranslatedLineOut.model_validate(ln, from_attributes=True).model_copy(update={"code_info": codes[ln.code]})
               for ln in bill.lines],
    )


@router.post("/{bill_id}/letters/request", response_model=LetterOut)
def make_request_letter(bill_id: int, body: LetterDetails | None = None,
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Letter asking the provider for a full itemized bill."""
    bill = _get_own_bill(db, bill_id, user)
    text = request_letter(body or LetterDetails(), bill_label=bill.label)
    return LetterOut(letter_type="request", bill_id=bill.id, text=text)


@router.post("/{bill_id}/letters/dispute", response_model=LetterOut)
def make_dispute_letter(bill_id: int, body: DisputeLetterRequest | None = None,
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Letter disputing the flags the check engine found. Send `flags` to include only the ones the
    patient confirmed; leave it empty to include all of them."""
    body = body or DisputeLetterRequest()
    bill = _get_own_bill(db, bill_id, user)
    engine_bill = bill.to_engine_bill()
    flags = run_checks(engine_bill).flags
    if body.flags:
        wanted = {(f.rule, f.line_no) for f in body.flags}
        unknown = wanted - {(f.rule, f.line_no) for f in flags}
        if unknown:
            rule, line_no = sorted(unknown, key=str)[0]
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                f"The check engine did not flag {rule} on line {line_no} for this bill")
        flags = [f for f in flags if (f.rule, f.line_no) in wanted]
    if not flags:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "There are no issues to dispute on this bill")
    codes = {c: lookup_code(c) for c in {ln.code for ln in bill.lines}}
    text = dispute_letter(engine_bill, flags, body, codes, bill_label=bill.label)
    return LetterOut(letter_type="dispute", bill_id=bill.id, text=text, flag_count=len(flags))