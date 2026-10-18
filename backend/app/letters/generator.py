"""Fills the request and dispute letter templates with real bill data.
The wording is fixed in the templates; nothing here decides what is an error.
The dispute letter only lists flags that the deterministic check engine produced."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from string import Template

from pydantic import BaseModel

from app.engine.models import Flag
from app.models.bill import Bill
from app.models.line_item import format_qty
from app.translation.lookup import CodeInfo

TEMPLATES = Path(__file__).parent / "templates"


class LetterDetails(BaseModel):
    """Details the patient fills in. Anything left blank becomes a [bracketed placeholder]."""
    patient_name: str | None = None
    patient_address: str | None = None
    provider_name: str | None = None
    provider_address: str | None = None
    account_number: str | None = None
    date_of_service: str | None = None


def _money(x: Decimal) -> str:
    return f"${x:,.2f}"


def _fill(d: LetterDetails, bill_label: str | None) -> dict[str, str]:
    return {
        "patient_name": d.patient_name or "[Your full name]",
        "patient_address": d.patient_address or "[Your mailing address]",
        "provider_name": d.provider_name or "[Hospital or provider name]",
        "provider_address": d.provider_address or "[Provider billing address]",
        "account_number": d.account_number or bill_label or "[Account number from your bill]",
        "date_of_service": d.date_of_service or "[Date(s) of service]",
        "today": date.today().strftime("%B %d, %Y").replace(" 0", " "),
    }


def _describe_line(bill: Bill, line_no: int, codes: dict[str, CodeInfo]) -> str:
    line = next(l for l in bill.lines if l.line_no == line_no)
    info = codes.get(line.code)
    plain = f" ({info.plain_english})" if info and info.plain_english else ""
    return f'line {line.line_no}, code {line.code}: "{line.description}"{plain}'


def _issue_text(n: int, flag: Flag, bill: Bill, codes: dict[str, CodeInfo]) -> str:
    if flag.rule == "duplicate_line":
        line = next(l for l in bill.lines if l.line_no == flag.line_no)
        lines = ", ".join(str(x) for x in flag.line_numbers)
        return (f"{n}. Possible duplicate charge - {_describe_line(bill, flag.line_no, codes)}.\n"
                f"   This appears to be the same charge as line {flag.related_line_no} (same code, quantity "
                f"{format_qty(line.quantity)} and unit price {_money(line.unit_price)}; lines {lines}). "
                f"I am questioning {_money(line.line_total)} for line {flag.line_no}.")
    if flag.rule == "line_math":
        line = next(l for l in bill.lines if l.line_no == flag.line_no)
        diff = flag.actual - flag.expected
        direction = "more" if diff > 0 else "less"
        return (f"{n}. Line total does not match quantity x unit price - {_describe_line(bill, flag.line_no, codes)}.\n"
                f"   {format_qty(line.quantity)} x {_money(line.unit_price)} = {_money(flag.expected)}, "
                f"but the bill shows {_money(flag.actual)} ({_money(abs(diff))} {direction} than expected).")
    if flag.rule == "subtotal_mismatch":
        diff = flag.actual - flag.expected
        direction = "more" if diff > 0 else "less"
        return (f"{n}. The subtotal does not match the charges listed.\n"
                f"   The line totals add up to {_money(flag.expected)}, but the subtotal shows "
                f"{_money(flag.actual)} ({_money(abs(diff))} {direction} than the listed charges).")
    return f"{n}. {flag.message}"


def request_letter(details: LetterDetails, bill_label: str | None = None) -> str:
    text = (TEMPLATES / "request_letter.txt").read_text(encoding="utf-8")
    return Template(text).substitute(_fill(details, bill_label))


def dispute_letter(bill: Bill, flags: list[Flag], details: LetterDetails,
                   codes: dict[str, CodeInfo], bill_label: str | None = None) -> str:
    if not flags:
        raise ValueError("There are no issues to dispute on this bill")
    issues = "\n\n".join(_issue_text(i, f, bill, codes) for i, f in enumerate(flags, start=1))
    count = len(flags)
    values = _fill(details, bill_label) | {
        "issues": issues,
        "issue_count_text": "1 item" if count == 1 else f"{count} items",
        "need_verb": "needs" if count == 1 else "need",
    }
    text = (TEMPLATES / "dispute_letter.txt").read_text(encoding="utf-8")
    return Template(text).substitute(values)