"""The flag report the check engine produces. Bill and LineItem live in app/models/."""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.bill import Bill  # noqa: F401  (re-exported for convenience)
from app.models.line_item import LineItem  # noqa: F401

Rule = Literal["duplicate_line", "line_math", "subtotal_mismatch"]


class Flag(BaseModel):
    rule: Rule
    line_no: int | None  # None for bill-level flags (subtotal)
    code: str | None
    severity: Literal["review"] = "review"  # we never say "error": the patient confirms or dismisses
    message: str
    expected: Decimal | None = None
    actual: Decimal | None = None
    related_line_no: int | None = None  # for duplicates: the earlier line it repeats
    line_numbers: list[int] = Field(default_factory=list)  # every line involved in this flag

class FlagReport(BaseModel):
    bill_id: str
    flag_count: int
    flags: list[Flag] = Field(default_factory=list)