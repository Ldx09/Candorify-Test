"""Request/response shapes for /api/bills. Money values are returned as strings (e.g. "234.00")
so no cents are lost to floating-point rounding; the frontend can display them as-is."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer


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