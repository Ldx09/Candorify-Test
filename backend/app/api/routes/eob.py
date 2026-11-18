"""Compare a bill with the patient's insurance EOB (Explanation of Benefits).

    POST   /api/bills/{id}/eob        EOB as a PDF (read in memory and deleted right away)
    POST   /api/bills/{id}/eob-text   EOB photos, read on the user's phone: only their text is sent
    DELETE /api/bills/{id}/eob        remove the EOB from this bill

Only the EOB's totals and service dates are kept on the bill; the file is never stored.
Every call returns all the bill's flags again, since the EOB checks (app/engine/checks/eob.py) may add some.
"""
import os
import tempfile
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.bills import get_own_bill
from app.core.database import get_db
from app.engine.checks.eob import asked_of_patient, same_visit
from app.engine.eob import read_eob_lines, read_eob_pdf
from app.engine.models import FlagReport
from app.models.eob import EobSummary
from app.models.user import User
from app.services.flags import sync_flags

router = APIRouter(prefix="/bills", tags=["eob"])

MAX_PDF_BYTES = 5 * 1024 * 1024
NOT_AN_EOB = ("We couldn't find insurance amounts in this file. Make sure it's the Explanation of Benefits (EOB) "
              "from your insurance company, not the bill itself.")


class EobTextIn(BaseModel):
    pages: list[list[Annotated[str, Field(max_length=300)]]] = Field(min_length=1, max_length=5)


class EobResult(BaseModel):
    bill_id: int
    eob: EobSummary | None
    same_visit: bool | None = None    # False: the EOB is for another date, so nothing was compared
    note: str | None = None           # shown under the EOB card
    flags: FlagReport                 # every flag on the bill, EOB checks included


def _save(db: Session, bill, eob: EobSummary | None) -> EobResult:
    bill.eob = eob.to_json() if eob else None
    db.commit()
    db.refresh(bill)
    flags = sync_flags(db, bill)
    engine_bill = bill.to_engine_bill()
    note = None
    visit = same_visit(engine_bill)
    if eob is not None:
        if visit is False:
            dates = ", ".join(d.strftime("%m/%d/%Y") for d in eob.service_dates[:3])
            note = (f"The service dates on this EOB ({dates}) don't match this bill's date of service "
                    f"({engine_bill.date_of_service:%m/%d/%Y}), so we didn't compare them. Check that it's the EOB "
                    f"for this visit.")
        elif eob.you_owe is not None and asked_of_patient(engine_bill) is None:
            note = ("To compare what you owe, fill in \"Your share\" or \"Still owed\" under Who paid what on the "
                    "Charges step.")
    return EobResult(bill_id=bill.id, eob=eob, same_visit=visit, note=note, flags=flags)


@router.post("/{bill_id}/eob", response_model=EobResult)
async def upload_eob_pdf(bill_id: int, file: UploadFile = File(..., description="Insurance EOB, PDF, max 5 MB"),
                         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bill = get_own_bill(db, bill_id, user)
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "The PDF is larger than 5 MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The file is not a PDF")
    fd, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        try:
            eob = read_eob_pdf(path)
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not read this PDF. Is it a valid PDF file?") from None
    finally:
        os.remove(path)
    if eob is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, NOT_AN_EOB)
    return _save(db, bill, eob)


@router.post("/{bill_id}/eob-text", response_model=EobResult)
def upload_eob_text(bill_id: int, body: EobTextIn, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    bill = get_own_bill(db, bill_id, user)
    if any(len(page) > 400 for page in body.pages):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too much text in one photo. Use one photo per page.")
    eob = read_eob_lines(body.pages)
    if eob is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, NOT_AN_EOB)
    return _save(db, bill, eob)


@router.delete("/{bill_id}/eob", response_model=EobResult)
def remove_eob(bill_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _save(db, get_own_bill(db, bill_id, user), None)