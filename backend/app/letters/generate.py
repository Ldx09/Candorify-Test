"""Generates the two letters from real bill data, using the templates in letters/templates/:
  - request-itemized-bill.txt : asks the provider for a full itemized bill
  - dispute.txt               : lists exactly the flagged lines and asks for a correction
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
from app.translation.service import CodeInfo

TEMPLATES = Path(__file__).parent / "templates"
REQUEST_TEMPLATE = TEMPLATES / "request-itemized-bill.txt"
DISPUTE_TEMPLATE = TEMPLATES / "dispute.txt"


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
    code = f", code {line.code}" if line.code.strip() else ""
    return f'line {line.line_no}{code}: "{line.description}"{plain}'

def _issue_text(n: int, flag: Flag, bill: Bill, codes: dict[str, CodeInfo]) -> str:
    if flag.rule == "duplicate_line":
        line = next(l for l in bill.lines if l.line_no == flag.line_no)
        lines = ", ".join(str(x) for x in flag.line_numbers)
        return (f"{n}. Possible duplicate charge - {_describe_line(bill, flag.line_no, codes)}.\n"
                f"   This appears to be the same charge as line {flag.related_line_no} "
                f"(same {'code' if line.code.strip() else 'description'}, quantity "                f"{format_qty(line.quantity)} and unit price {_money(line.unit_price)}; lines {lines}). "
                f"I am questioning {_money(line.line_total)} for line {flag.line_no}.")
    if flag.rule == "line_math":
        line = next(l for l in bill.lines if l.line_no == flag.line_no)
        diff = flag.actual - flag.expected
        direction = "more" if diff > 0 else "less"
        return (f"{n}. Line total does not match quantity x unit price - {_describe_line(bill, flag.line_no, codes)}.\n"
                f"   {format_qty(line.quantity)} x {_money(line.unit_price)} = {_money(flag.expected)}, "
                f"but the bill shows {_money(flag.actual)} ({_money(abs(diff))} {direction} than expected).")
    if flag.rule == "answer_mismatch":
        lines = flag.line_numbers or [flag.line_no]
        where = _describe_line(bill, lines[0], codes)
        if len(lines) > 1:
            where += f" (and line{'s' if len(lines) > 2 else ''} {', '.join(str(n) for n in lines[1:])})"
        return (f"{n}. Charge does not match the care I received - {where}.\n"
                f"   {flag.letter_text or flag.message}")
    if flag.rule == "eob_owe_mismatch":
        return (f"{n}. The amount I am asked to pay is more than my insurance's Explanation of Benefits (EOB) shows.\n"
                f"   My EOB states that my responsibility for this visit is {_money(flag.expected)}, but the bill asks "
                f"me to pay {_money(flag.actual)}. Please correct my balance to match the EOB, or explain the "
                f"difference in writing.")
    if flag.rule == "eob_paid_mismatch":
        return (f"{n}. The insurance payment on my bill does not match my EOB.\n"
                f"   My EOB states that my plan paid {_money(flag.expected)}, but the bill shows "
                f"{_money(flag.actual)}. Please check that the full insurance payment was applied to my account.")
    if flag.rule == "eob_billed_mismatch":
        return (f"{n}. The total on my bill does not match the amount billed on my EOB.\n"
                f"   My EOB lists {_money(flag.expected)} billed for this visit, but the bill's total is "
                f"{_money(flag.actual)}. Please explain the difference and confirm all charges were sent to my insurance.")
        
    if flag.rule == "payment_mismatch":
        p = bill.payments
        if p is not None and (p.insurance_paid is not None or p.adjustments is not None):
            steps = [f"charges {_money(bill.stated_subtotal)}"] + [
                f"{label} {_money(v)}" for v, label in ((p.insurance_paid, "insurance paid"), (p.adjustments, "discounts"),
                                                        (p.other_payments, "other payments"), (p.patient_paid, "my payments"))
                if v is not None]
            how = f"{', '.join(steps)}: that leaves {_money(flag.expected)}"
        else:
            how = f"my share minus what I paid leaves {_money(flag.expected)}"
        return (f"{n}. The payments on my account do not add up to the balance I am asked to pay.\n"
                f"   {how}, but the bill asks me to pay {_money(flag.actual)}. Please send me an itemized account "
                f"history showing every payment and adjustment, and correct my balance.")
    if flag.rule == "overpaid":
        p = bill.payments
        if p is not None and p.patient_paid is not None and p.patient_responsibility is not None \
                and p.patient_paid > p.patient_responsibility:
            why = (f"I paid {_money(p.patient_paid)}, but my share was {_money(p.patient_responsibility)}, so I may be "
                   f"owed {_money(p.patient_paid - p.patient_responsibility)}.")
        else:
            why = f"My account shows a credit of {_money(abs(p.balance_due)) if p and p.balance_due is not None else 'an amount'}."
        return (f"{n}. I may have overpaid and be owed a refund.\n"
                f"   {why} Please confirm the amount and refund it to me.")
    if flag.rule == "subtotal_mismatch":
        diff = flag.actual - flag.expected
        direction = "more" if diff > 0 else "less"
        return (f"{n}. The subtotal does not match the charges listed.\n"
                f"   The line totals add up to {_money(flag.expected)}, but the subtotal shows "
                f"{_money(flag.actual)} ({_money(abs(diff))} {direction} than the listed charges).")
    return f"{n}. {flag.message}"


def request_letter(details: LetterDetails, bill_label: str | None = None) -> str:
    text = REQUEST_TEMPLATE.read_text(encoding="utf-8")
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
    text = DISPUTE_TEMPLATE.read_text(encoding="utf-8")
    return Template(text).substitute(values)