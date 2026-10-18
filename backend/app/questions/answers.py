"""Checks the patient's answers against the bill. Plain code only: Gemini never decides a flag.

Rules (Mariz's question bank doc):
  * Skipped answers and "Not sure" never create a flag ("Not sure" is accepted for every question,
    including number ones).
  * Number answers flag only when LOWER than what was billed (a higher answer is not an overcharge);
    ambulance miles flag only when under 80% of the billed miles (people estimate).
  * Yes/no and choice answers flag on the specific answer the question bank names (e.g. "No").
  * Choice answers are stored and compared as the English label, whatever language the patient used.
"""
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel

from app.models.line_item import format_qty
from app.questions.bank import BANK, QuestionType
from app.questions.picker import Question


NOT_SURE = "Not sure"


class AnswerError(ValueError):
    pass


class AnswerResult(BaseModel):
    question_id: str
    value: str | None        # normalized: English label, number as text, or None (skipped)
    mismatch: bool
    flag_message: str | None = None
    letter_text: str | None = None
    billed: Decimal | None = None
    answered: Decimal | None = None


def normalize(qt: QuestionType, question_id: str, value) -> str | Decimal | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None  # skipped
    if isinstance(value, str) and value.strip().lower() == NOT_SURE.lower():
        return NOT_SURE  # allowed for every question, even number ones; never flags
    if qt.answer_type == "number":
        if isinstance(value, bool):
            raise AnswerError(f"The answer to {question_id} must be a number")
        try:
            num = Decimal(str(value).strip())
        except InvalidOperation:
            raise AnswerError(f"The answer to {question_id} must be a number") from None
        if not num.is_finite() or num < 0 or num > 100000:
            raise AnswerError(f"The answer to {question_id} must be a number between 0 and 100000")
        return num
    if qt.answer_type == "yes_no" and isinstance(value, bool):
        return "Yes" if value else "No"
    text = str(value).strip().replace("_", " ").lower()
    for choice in qt.choices or []:
        if text == choice.lower():
            return choice
    raise AnswerError(f"The answer to {question_id} must be one of: {', '.join(qt.choices or [])}")


def _fill(template: str, **values) -> str:
    for k, v in values.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def evaluate(question: Question, value) -> AnswerResult:
    qt = BANK.get(question.type)
    norm = normalize(qt, question.id, value)
    if norm is None or norm == NOT_SURE:
        return AnswerResult(question_id=question.id, value=norm, mismatch=False)
    check = qt.check
    if check.kind == "number_lower":
        mismatch = norm < question.billed_qty
    elif check.kind == "number_below_ratio":
        mismatch = norm < question.billed_qty * check.ratio
    else:
        mismatch = norm == check.value
    stored = format_qty(norm) if isinstance(norm, Decimal) else norm
    result = AnswerResult(question_id=question.id, value=stored, mismatch=mismatch)
    if mismatch:
        values = dict(answer=stored, billed=format_qty(question.billed_qty), description=question.description,
                      minutes=question.minutes if question.minutes is not None else "",
                      date_phrase=f" on {question.date}" if question.date else "")
        result.flag_message = _fill(qt.flag_message, **values)
        result.letter_text = _fill(qt.letter_text, **values)
        result.billed = question.billed_qty
        result.answered = norm if isinstance(norm, Decimal) else None
    return result