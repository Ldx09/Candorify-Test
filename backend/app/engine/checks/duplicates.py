"""Duplicate-line detector: catches the same charge billed twice.

Two lines are duplicates when they have the same code, unit price and quantity.
The wording is ignored, so "Comprehensive metabolic panel" and "CMP lab panel"
with code 80053 at the same price and qty are still duplicates.
The same code with a different price or quantity is NOT flagged: that is often legitimate.
"""
from decimal import Decimal

from app.engine.models import Bill, Flag
from app.models.line_item import format_qty


def _key(code: str, unit_price: Decimal, quantity: Decimal) -> tuple:
    # normalize() makes 22, 22.0 and 22.00 compare equal
    return (code.strip().upper(), unit_price.normalize(), quantity.normalize())


def check_duplicates(bill: Bill) -> list[Flag]:
    """Emits one flag for every repeat of a charge (a charge billed 3 times gives 2 flags).
    Each flag names the repeated line, the first occurrence, and all lines in the group."""
    groups: dict[tuple, list[int]] = {}
    for line in bill.lines:
        groups.setdefault(_key(line.code, line.unit_price, line.quantity), []).append(line.line_no)

    by_line_no = {line.line_no: line for line in bill.lines}
    flags: list[Flag] = []
    for line_nos in groups.values():
        if len(line_nos) < 2:
            continue
        first = line_nos[0]
        for repeat in line_nos[1:]:
            line = by_line_no[repeat]
            others = ", ".join(str(n) for n in line_nos)
            flags.append(Flag(
                rule="duplicate_line",
                line_no=repeat,
                code=line.code,
                related_line_no=first,
                line_numbers=line_nos,
                message=(f"Line {repeat} repeats line {first}: same code {line.code}, quantity "
                         f"{format_qty(line.quantity)}, unit price ${line.unit_price:,.2f} (lines {others}). "
                         f"You may have been charged twice for the same item."),
            ))
    return sorted(flags, key=lambda f: f.line_no)