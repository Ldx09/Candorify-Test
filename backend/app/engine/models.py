"""The flag report the check engine produces. Bill and LineItem live in app/models/."""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.bill import Bill  # noqa: F401  (re-exported for convenience)
from app.models.line_item import LineItem  # noqa: F401

Rule = Literal["duplicate_line", "line_math", "subtotal_mismatch", "answer_mismatch"]
ENGINE_RULES = ("duplicate_line", "line_math", "subtotal_mismatch")  # decided by the check engine itself


class Flag(BaseModel):
    id: int | None = None       # set once the flag is saved for a stored bill
    status: Literal["investigating", "add_to_letter", "dismissed"] | None = None  # set by the user
    rule: Rule
    line_no: int | None  # None for bill-level flags (subtotal)
    code: str | None
    severity: Literal["review"] = "review"  # we never say "error": the patient confirms or dismisses
    message: str
    expected: Decimal | None = None
    actual: Decimal | None = None
    related_line_no: int | None = None  # for duplicates: the earlier line it repeats
    line_numbers: list[int] = Field(default_factory=list)  # every line involved in this flag
    question_id: str | None = None   # answer_mismatch only: the follow-up question it came from
    letter_text: str | None = None   # answer_mismatch only: first-person sentence for the dispute letter


class FlagReport(BaseModel):
    bill_id: str
    flag_count: int
    flags: list[Flag] = Field(default_factory=list)