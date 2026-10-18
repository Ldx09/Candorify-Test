"""POST /api/letters -- generates the request or dispute letter for one of the user's bills. Protected."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.bills import get_own_bill
from app.core.database import get_db
from app.engine.models import Flag
from app.letters.generate import dispute_letter, request_letter
from app.models.user import User
from app.schemas.letters import LetterOut, LetterRequest, LetterTranslation
from app.services.flags import stored_flags
from app.translation.service import lookup_code
from app.translation.translator import translate_texts

router = APIRouter(tags=["letters"])


def _bad(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, msg)


def _choose_flags(all_flags: list[Flag], body: LetterRequest) -> list[Flag]:
    if body.flag_ids:
        by_id = {f.id: f for f in all_flags}
        unknown = [i for i in body.flag_ids if i not in by_id]
        if unknown:
            raise _bad(f"Flag {unknown[0]} is not a flag on this bill")
        wanted = set(body.flag_ids)
        return [f for f in all_flags if f.id in wanted]
    if body.flags:
        wanted = {(f.rule, f.line_no) for f in body.flags}
        unknown = wanted - {(f.rule, f.line_no) for f in all_flags}
        if unknown:
            rule, line_no = sorted(unknown, key=str)[0]
            where = f"line {line_no}" if line_no is not None else "the subtotal"
            raise _bad(f"The check engine did not flag {rule} on {where} for this bill")
        return [f for f in all_flags if (f.rule, f.line_no) in wanted]
    marked = [f for f in all_flags if f.status == "add_to_letter"]
    return marked or [f for f in all_flags if f.status != "dismissed"]


def _with_translation(out: LetterOut, body: LetterRequest, bill_label: str | None) -> LetterOut:
    """Adds a read-only copy in the user's language. Personal details are masked before translation."""
    if not body.language:
        return out
    protect = [body.patient_name, body.patient_address, body.account_number or bill_label]
    result = translate_texts([out.text], body.language, protect=[p for p in protect if p])
    item = result.items[0]
    out.translation = LetterTranslation(language=result.language.code, language_name=result.language.name,
                                        rtl=result.language.rtl, text=item.text, translated=item.translated,
                                        note=result.note or "")
    return out


@router.post("/letters", response_model=LetterOut)
def create_letter(body: LetterRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """letter_type "request": asks the provider for a full itemized bill.
    letter_type "dispute": lists exactly the chosen flags. By default that is the flags marked
    "add_to_letter" (or, if none are marked yet, every flag that isn't "dismissed").
    `language` (optional): also returns a read-only translated copy; the letter to send stays in English."""
    bill = get_own_bill(db, body.bill_id, user)

    if body.letter_type == "request":
        out = LetterOut(letter_type="request", bill_id=bill.id, text=request_letter(body, bill_label=bill.label))
        return _with_translation(out, body, bill.label)

    all_flags = stored_flags(db, bill)
    if not all_flags:
        raise _bad("There are no issues to dispute on this bill")
    flags = _choose_flags(all_flags, body)
    if not flags:
        raise _bad("All flags on this bill are dismissed. Mark at least one as add_to_letter to write a dispute letter")

    codes = {c: lookup_code(c) for c in {ln.code for ln in bill.lines}}
    text = dispute_letter(bill.to_engine_bill(), flags, body, codes, bill_label=bill.label)
    out = LetterOut(letter_type="dispute", bill_id=bill.id, text=text, flag_count=len(flags),
                    flagged_lines=sorted({f.line_no for f in flags if f.line_no is not None}),
                    flag_ids=[f.id for f in flags])
    return _with_translation(out, body, bill.label)