"""Upload a bill and answer its follow-up questions.

    POST /api/upload/pdf     PDF bill -> stored bill + engine flags + follow-up questions
    POST /api/upload/sample  same, for a sample bill (demo / testing without a PDF)
    POST /api/upload/review  the patient's answers -> answer_mismatch flags

The uploaded PDF is read in memory/temp and deleted right away; only the bill lines are stored.

Two readers: our synthetic/demo layout first (unchanged), and only if that can't read the PDF, the
real-bill reader (app/engine/real_bills.py) for hospital and doctor statements.
"""
import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.bills import check_language, get_own_bill, make_sample_bill, save_bill
from app.core.database import get_db
from app.engine.loader import load_bills_pdf
from app.engine.real_bills import read_real_bill
from app.models.bill import Bill
from app.models.user import User
from app.questions.answers import AnswerError
from app.questions.localize import localize_questions
from app.schemas.bills import BillOut, SampleBillRequest
from app.schemas.questions import ReviewIn, ReviewResult, UploadResult
from app.services.answers import bill_questions, save_answers
from app.services.flags import sync_flags

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_PDF_BYTES = 5 * 1024 * 1024


class SampleUploadRequest(SampleBillRequest):
    language: str | None = None


SUMMARY_NOTICE = ("This looks like a summary bill: it lists charges but not the quantity and price of each item. "
                  "We checked the total and looked for repeated charges. To check every charge, ask your provider "
                  "for a fully itemized bill (you can use our request letter).")
NO_TOTAL_NOTICE = " We couldn't find a total on this bill, so we added up the charges ourselves."
REAL_BILL_LABEL = "Uploaded bill"
UNREADABLE = ("We couldn't find any charges in this PDF. Make sure it's a bill with a list of charges "
              "(not a scanned photo), or enter the charges by hand.")


def _result(db: Session, user: User, bill: Bill, label: str, language: str | None,
            bill_format: str = "itemized", notice: str | None = None) -> UploadResult:
    record = save_bill(db, user, bill, label)
    flags = sync_flags(db, record)
    loc = localize_questions(bill_questions(record), language)
    return UploadResult(bill=BillOut.model_validate(record), flags=flags, questions=loc.questions,
                        language=loc.language, rtl=loc.rtl, translation_note=loc.note,
                        bill_format=bill_format, notice=notice)


def _read_pdf(data: bytes) -> tuple[list[Bill], str | None]:
    """Returns (bills, notice). notice is None for our itemized layout and set for real summary bills."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        try:
            bills = [b for b in load_bills_pdf(path) if b.lines]
            if bills:
                return bills, None
        except ValueError:
            pass  # not our layout: try the real-bill reader below
        real = read_real_bill(path)
        if real is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, UNREADABLE)
        return [real.bill], SUMMARY_NOTICE + ("" if real.has_total else NO_TOTAL_NOTICE)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not read this PDF. Is it a valid PDF file?") from None
    finally:
        os.remove(path)


@router.post("/pdf", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(..., description="Itemized bill, PDF, max 5 MB"),
                     account: str | None = Form(default=None, max_length=40,
                                                description="Which bill, if the PDF has more than one"),
                     language: str | None = Form(default=None, max_length=10,
                                                 description="Language for the questions, e.g. es"),
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Reads the PDF, stores the bill, runs the check engine and returns the follow-up questions."""
    check_language(language)
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "The PDF is larger than 5 MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The file is not a PDF")
    bills, notice = _read_pdf(data)
    if notice is not None:  # a real summary bill: one bill, no account numbers kept
        return _result(db, user, bills[0], REAL_BILL_LABEL, language, bill_format="summary", notice=notice)
    if account:
        bills = [b for b in bills if b.bill_id.upper() == account.strip().upper()]
        if not bills:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Account '{account}' is not in this PDF")
    elif len(bills) > 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "This PDF has more than one bill. Send `account` with one of: "
                            + ", ".join(b.bill_id for b in bills))
    return _result(db, user, bills[0], bills[0].bill_id, language)


@router.post("/sample", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
def upload_sample(body: SampleUploadRequest | None = None, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """Same response as /pdf, for a sample bill: {"sample_id": "DEMO-001", "language": "es"}."""
    body = body or SampleUploadRequest()
    check_language(body.language)
    bill, label = make_sample_bill(body)
    return _result(db, user, bill, label, body.language)


@router.post("/review", response_model=ReviewResult)
def review(body: ReviewIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Saves the patient's answers. Answers that don't match the bill become answer_mismatch flags
    (status "investigating"; they can be added to the dispute letter like any other flag).
    "Not sure" and skipped (null) answers never create a flag. Sending answers again replaces the old ones."""
    bill = get_own_bill(db, body.bill_id, user)
    try:
        report, new_ids = save_answers(db, bill, [(a.question_id, a.value) for a in body.answers])
    except AnswerError as exc:
        raise HTTPException(422, str(exc)) from None
    return ReviewResult(bill_id=bill.id, answers_saved=len(body.answers), new_flag_ids=new_ids, flags=report)