"""Request/response shapes for /api/bills. Money values are returned as strings (e.g. "234.00")
so no cents are lost to floating-point rounding; the frontend can display them as-is."""
from datetime import datetime
from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, Field, field_serializer

from app.translation.service import CodeInfo


class LineIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    line_total: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class BillIn(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    stated_subtotal: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    lines: list[LineIn] = Field(min_length=1, max_length=500)  # line numbers are assigned 1, 2, 3... in order


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
    created_at: datetime
    lines: list[LineOut]

    model_config = {"from_attributes": True}


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
    """Demo helper. Give sample_id (e.g. "BILL-001") to load one of the 20 provided synthetic bills,
    or leave it out to generate a fresh synthetic bill with a planted error."""
    sample_id: str | None = Field(default=None, max_length=20)
    defect: Literal["none", "duplicate", "line_math", "subtotal", "mixed"] | None = None  # for generated bills


class FlagStatusUpdate(BaseModel):
    status: Literal["investigating", "add_to_letter", "dismissed"]