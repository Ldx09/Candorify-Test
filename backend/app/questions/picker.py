"""Picks the follow-up questions for a bill from the question bank. Plain code only (no AI), so every
bill always gets its questions, the same ones every time.

Rules (Mariz's question bank doc):
 1. Match each line's code against each question type's code ranges.
 2. Group: "type" questions add up quantity across all their lines and are asked once;
    "code" questions are asked once per distinct code.
 3. Order: room and ICU nights first, then by line total (highest first). Stop at 5.
 4. Skip lines with quantity 0 or no description.
"""
from decimal import Decimal

from pydantic import BaseModel

from app.models.bill import Bill
from app.models.line_item import format_qty
from app.questions.bank import BANK, QuestionBank, QuestionType


class Question(BaseModel):
    id: str                       # stable: "room_nights" or "supplies_received:A6402"
    type: str                     # question type id from the bank
    text: str                     # default English wording, filled in from the bill
    answer_type: str              # number | yes_no | choice
    choices: list[str] | None     # English labels (send back the English label as the answer value)
    line_refs: list[int]          # which bill lines it is about
    # Context the answer check needs (kept server-side; not needed by the frontend):
    billed_qty: Decimal
    description: str
    code: str
    minutes: int | None = None
    date: str | None = None


def _fill(template: str, **values) -> str:
    out = template
    for k, v in values.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def pick_questions(bill: Bill, date_of_service: str | None = None, bank: QuestionBank = BANK) -> list[Question]:
    groups: dict[str, dict] = {}
    for line in bill.lines:
        if line.quantity <= 0 or not line.description.strip():
            continue
        code = line.code.strip().upper()
        for qt in bank.questions:
            if not qt.matches(code):
                continue
            key = qt.id if qt.group == "type" else f"{qt.id}:{code}"
            g = groups.setdefault(key, {"qt": qt, "lines": [], "qty": Decimal(0), "total": Decimal(0),
                                        "description": line.description.strip(), "code": code})
            g["lines"].append(line.line_no)
            g["qty"] += line.quantity
            g["total"] += line.line_total

    ordered = sorted(groups.items(), key=lambda kv: (kv[1]["qt"].priority, -kv[1]["total"], kv[1]["lines"][0]))
    questions = []
    for key, g in ordered[: bank.max_questions]:
        qt: QuestionType = g["qt"]
        minutes = int(g["qty"] * 15) if qt.id == "therapy_time" else None
        template = qt.text if (date_of_service or not qt.text_no_date) else qt.text_no_date
        text = _fill(template, qty=format_qty(g["qty"]), description=g["description"],
                     date=date_of_service or "", minutes=minutes if minutes is not None else "")
        questions.append(Question(id=key, type=qt.id, text=text, answer_type=qt.answer_type, choices=qt.choices,
                                  line_refs=g["lines"], billed_qty=g["qty"], description=g["description"],
                                  code=g["code"], minutes=minutes, date=date_of_service))
    return questions