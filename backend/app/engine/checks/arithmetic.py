"""Arithmetic checks: line math (unit price x qty = line total) and subtotal (sum of lines)."""
from decimal import Decimal

from app.engine.models import Bill, Flag
from app.models.line_item import format_qty

# Differences up to 1 cent are treated as rounding, not errors.
TOLERANCE = Decimal("0.01")


def _money(x: Decimal) -> str:
    return f"${x:,.2f}"


def check_line_math(bill: Bill) -> list[Flag]:
    """Flags lines where unit price x quantity does not equal the line total."""
    flags: list[Flag] = []
    for line in bill.lines:
        expected = (line.unit_price * line.quantity).quantize(Decimal("0.01"))
        if abs(expected - line.line_total) > TOLERANCE:
            flags.append(Flag(
                rule="line_math",
                line_no=line.line_no,
                code=line.code,
                line_numbers=[line.line_no],
                expected=expected,
                actual=line.line_total,
                message=(f"Line {line.line_no}{f' ({line.code})' if line.code.strip() else ''}: "
                         f"{format_qty(line.quantity)} x {_money(line.unit_price)} "
                         f"= {_money(expected)}, but the bill shows {_money(line.line_total)}."),
            ))
    return flags


def check_subtotal(bill: Bill) -> list[Flag]:
    """Flags the bill if the sum of the line totals does not equal the stated subtotal."""
    total = sum((line.line_total for line in bill.lines), Decimal("0"))
    if abs(total - bill.stated_subtotal) > TOLERANCE:
        return [Flag(
            rule="subtotal_mismatch",
            line_no=None,
            code=None,
            expected=total,
            actual=bill.stated_subtotal,
            message=(f"The line totals add up to {_money(total)}, but the bill's subtotal "
                     f"says {_money(bill.stated_subtotal)}."),
        )]
    return []