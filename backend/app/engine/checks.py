"""Deterministic check engine. Plain rules and arithmetic only: no AI in the error-finding step.

Same bill in -> same flags out, every time.
"""
from decimal import Decimal

from app.engine.models import Bill, Flag, FlagReport

# Differences up to 1 cent are treated as rounding, not errors.
TOLERANCE = Decimal("0.01")


def _money(x: Decimal) -> str:
    return f"${x:,.2f}"


def check_duplicates(bill: Bill) -> list[Flag]:
    """Flags any line whose code already appeared earlier on the bill.
    Matches on the code only, so the same code with different wording is still a duplicate."""
    flags: list[Flag] = []
    first_seen: dict[str, int] = {}
    for line in bill.lines:
        code = line.code.strip().upper()
        if code in first_seen:
            flags.append(Flag(
                rule="duplicate_line",
                line_no=line.line_no,
                code=line.code,
                related_line_no=first_seen[code],
                message=(f"Line {line.line_no} repeats code {line.code} from line {first_seen[code]}. "
                         f"You may have been charged twice for the same item."),
            ))
        else:
            first_seen[code] = line.line_no
    return flags


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
                expected=expected,
                actual=line.line_total,
                message=(f"Line {line.line_no} ({line.code}): {line.quantity} x {_money(line.unit_price)} "
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


def run_checks(bill: Bill) -> FlagReport:
    """Runs every check on one bill and returns the flag report."""
    flags = check_duplicates(bill) + check_line_math(bill) + check_subtotal(bill)
    return FlagReport(bill_id=bill.bill_id, flag_count=len(flags), flags=flags)