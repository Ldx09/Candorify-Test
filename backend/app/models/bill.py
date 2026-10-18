"""An itemized medical bill: the structure every check runs on."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.line_item import LineItem


class Bill(BaseModel):
    bill_id: str
    lines: list[LineItem]
    stated_subtotal: Decimal  # the subtotal / total charges printed on the bill
    date_of_service: date | None = None