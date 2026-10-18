"""Data model for a bill and the flag report the check engine produces."""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    line_no: int
    code: str  # kept as text: codes like "0250" have a leading zero
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal  # the total printed on the bill (may be wrong; that's what we check)


class Bill(BaseModel):
    bill_id: str
    lines: list[LineItem]
    stated_subtotal: Decimal  # the subtotal printed on the bill


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


class FlagReport(BaseModel):
    bill_id: str
    flag_count: int
    flags: list[Flag] = Field(default_factory=list)