"""Request/response shapes for /api/bills. Money values are returned as strings (e.g. "234.00")
so no cents are lost to floating-point rounding; the frontend can display them as-is."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.models.eob import EobSummary
from app.models.payments import Payments
from app.translation.service import CodeInfo


class LineIn(BaseModel):
    code: str = Field(default="", max_length=20)  # may be blank: real summary bills often print no codes
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    line_total: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class BillIn(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    stated_subtotal: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    date_of_service: date | None = None  # "2026-09-01"
    lines: list[LineIn] = Field(min_length=1, max_length=500)  # line numbers are assigned 1, 2, 3... in order
    payments: Payments | None = None  # who paid what, as checked by the user (optional)
    eob: EobSummary | None = None     # insurance EOB totals, kept when the charges are edited (optional)


class LineOut(BaseModel):
    line_no: int
    code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}

    @field_serializer("quantity")
    def _qty(self, q: Decimal) -> str:  # "3.000" from the database -> "3"
        return format(q.normalize(), "f")


class BillOut(BaseModel):
    id: int
    label: str | None
    stated_subtotal: Decimal
    date_of_service: date | None = None
    created_at: datetime
    lines: list[LineOut]
    payments: Payments | None = None   # who paid what, when the bill shows it
    eob: EobSummary | None = None      # insurance EOB totals, when the user added an EOB

    model_config = {"from_attributes": True}

    @field_validator("payments", mode="before")
    @classmethod
    def _payments(cls, v):   # stored as JSON text in the database
        return Payments.from_json(v) if isinstance(v, str) or v is None else v

    @field_validator("eob", mode="before")
    @classmethod
    def _eob(cls, v):        # stored as JSON text in the database
        return EobSummary.from_json(v) if isinstance(v, str) or v is None else v


class TranslatedLineOut(LineOut):
    code_info: CodeInfo | None = None
    plain_english_translated: str | None = None  # only when ?language= is given and translation worked


class TranslatedBillOut(BaseModel):
    id: int
    label: str | None
    stated_subtotal: Decimal
    lines: list[TranslatedLineOut]
    language: str | None = None
    rtl: bool = False
    translation_note: str | None = None


class BillSummary(BaseModel):
    id: int
    label: str | None
    stated_subtotal: Decimal
    line_count: int
    created_at: datetime
    expires_at: datetime  # deleted automatically after this (retention)


class SampleBillRequest(BaseModel):
    """Demo helper. Give sample_id to load a provided bill: BILL-001..BILL-020 (synthetic set) or
    DEMO-001..DEMO-004 (demo bills that trigger the follow-up questions). Leave it out to generate a
    fresh synthetic bill with a planted error."""
    sample_id: str | None = Field(default=None, max_length=20)
    defect: Literal["none", "duplicate", "line_math", "subtotal", "mixed"] | None = None  # for generated bills


class FlagStatusUpdate(BaseModel):
    status: Literal["investigating", "add_to_letter", "dismissed"]