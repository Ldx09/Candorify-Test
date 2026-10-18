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
from app.schemas.bills import BillIn, BillOut

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