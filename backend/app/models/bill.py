"""An itemized medical bill: the structure every check runs on."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.eob import EobSummary
from app.models.line_item import LineItem
from app.models.payments import Payments


class Bill(BaseModel):
    bill_id: str
    lines: list[LineItem]
    stated_subtotal: Decimal  # the subtotal / total charges printed on the bill
    date_of_service: date | None = None
    payments: Payments | None = None  # who paid what, when the bill shows it
    eob: EobSummary | None = None     # the totals from the patient's insurance EOB, if they added one