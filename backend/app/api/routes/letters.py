"""POST /api/letters -- generates the request or dispute letter for one of the user's bills. Protected."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.bills import get_own_bill
from app.core.database import get_db
from app.engine.checks import run_checks
from app.letters.generate import dispute_letter, request_letter
from app.models.user import User
from app.schemas.letters import LetterOut, LetterRequest
from app.translation.service import lookup_code

router = APIRouter(tags=["letters"])


@router.post("/letters", response_model=LetterOut)
def create_letter(body: LetterRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """letter_type "request": asks the provider for a full itemized bill.
    letter_type "dispute": lists exactly the lines the check engine flagged. Send `flags` to include only
    the ones the patient confirmed; leave it empty to include all of them."""
    bill = get_own_bill(db, body.bill_id, user)

    if body.letter_type == "request":
        return LetterOut(letter_type="request", bill_id=bill.id, text=request_letter(body, bill_label=bill.label))

    engine_bill = bill.to_engine_bill()
    flags = run_checks(engine_bill).flags
    if body.flags:
        wanted = {(f.rule, f.line_no) for f in body.flags}
        unknown = wanted - {(f.rule, f.line_no) for f in flags}
        if unknown:
            rule, line_no = sorted(unknown, key=str)[0]
            where = f"line {line_no}" if line_no is not None else "the subtotal"
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                f"The check engine did not flag {rule} on {where} for this bill")
        flags = [f for f in flags if (f.rule, f.line_no) in wanted]
    if not flags:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "There are no issues to dispute on this bill")

    codes = {c: lookup_code(c) for c in {ln.code for ln in bill.lines}}
    text = dispute_letter(engine_bill, flags, body, codes, bill_label=bill.label)
    flagged_lines = sorted({f.line_no for f in flags if f.line_no is not None})
    return LetterOut(letter_type="dispute", bill_id=bill.id, text=text,
                     flag_count=len(flags), flagged_lines=flagged_lines)