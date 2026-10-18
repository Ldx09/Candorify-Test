"""Saves the patient's answers and turns mismatches into answer_mismatch flags.

Each review replaces the bill's previous answers. An answer flag that still applies keeps the status
the patient gave it; answer flags that no longer apply are removed.
"""
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.engine.models import FlagReport
from app.models.answer_record import AnswerRecord
from app.models.bill_record import BillRecord
from app.models.flag_record import DEFAULT_STATUS, FlagRecord
from app.questions.answers import AnswerError, evaluate  # noqa: F401  (AnswerError raised from here)
from app.questions.picker import Question, pick_questions
from app.services.flags import all_flags, sync_flags


def bill_questions(bill: BillRecord) -> list[Question]:
    dos = bill.date_of_service.strftime("%m/%d/%Y") if bill.date_of_service else None
    return pick_questions(bill.to_engine_bill(), date_of_service=dos)


def save_answers(db: Session, bill: BillRecord, answers: list[tuple[str, object]]) -> tuple[FlagReport, list[int]]:
    """answers: [(question_id, value)]. Raises AnswerError for unknown questions or invalid values.
    Returns (all flags on the bill, ids of the answer flags that are new in this review)."""
    questions = {q.id: q for q in bill_questions(bill)}
    seen = set()
    results = []
    for qid, value in answers:
        if qid not in questions:
            raise AnswerError(f"'{qid}' is not a question for this bill")
        if qid in seen:
            raise AnswerError(f"'{qid}' was answered more than once")
        seen.add(qid)
        results.append((questions[qid], evaluate(questions[qid], value)))

    sync_flags(db, bill)  # make sure the engine flags exist too
    old_flags = {r.question_id: r for r in db.scalars(
        select(FlagRecord).where(FlagRecord.bill_id == bill.id, FlagRecord.rule == "answer_mismatch"))}
    db.execute(delete(AnswerRecord).where(AnswerRecord.bill_id == bill.id))
    keep: set[str] = set()
    for q, r in results:
        db.add(AnswerRecord(bill_id=bill.id, question_id=q.id, question_type=q.type, value=r.value))
        if not r.mismatch:
            continue
        keep.add(q.id)
        rec = old_flags.get(q.id)
        if rec is None:
            rec = FlagRecord(bill_id=bill.id, rule="answer_mismatch", question_id=q.id, status=DEFAULT_STATUS)
            db.add(rec)
        rec.line_no, rec.code = q.line_refs[0], q.code
        rec.line_numbers = json.dumps(q.line_refs)
        rec.message, rec.letter_text = r.flag_message, r.letter_text
        rec.expected, rec.actual = r.billed, r.answered
    for qid, rec in old_flags.items():
        if qid not in keep:
            db.delete(rec)
    db.commit()
    report = all_flags(db, bill)
    new_ids = [f.id for f in report.flags if f.rule == "answer_mismatch" and f.question_id in keep
               and f.question_id not in old_flags]
    return report, new_ids


def saved_answers(db: Session, bill: BillRecord) -> dict[str, str | None]:
    return {a.question_id: a.value for a in db.scalars(select(AnswerRecord).where(AnswerRecord.bill_id == bill.id))}