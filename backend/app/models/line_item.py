"""One charge line on an itemized medical bill."""
from decimal import Decimal

from pydantic import BaseModel


def format_qty(q: Decimal) -> str:
    """3.000 -> "3", 1.500 -> "1.5" (for messages shown to users)."""
    text = format(q.normalize(), "f")
    return text


class LineItem(BaseModel):
    line_no: int
    code: str  # kept as text: codes like "0250" have a leading zero
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal  # the total printed on the bill (may be wrong; that's what the engine checks)