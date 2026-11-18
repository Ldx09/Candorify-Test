"""Finds who paid what on a bill, from its text lines (PDF text or the text read from photos).

Bills show payments in many ways, for example:
    Insurance covered -$36,230.56 / Remaining responsibility $550.00 / Mychart Payment -$550.00   (MyChart)
    Adjustments: -$5,741.45 / Insurance Payments -$30,489.11 / Total Amount Due: $550.00          (statements)
    12/02/2025 Insurance Payment - BCBS 230.07 / Charges Credits Balance columns                  (doctors)
Each line with an amount is sorted into a bucket by its words (see the patterns below). A bucket that has
a summary line ("Insurance Payments", "Total ...") uses it; otherwise its single payments are added up,
so nothing is counted twice. Only what the bill shows is kept: a bucket the bill doesn't mention stays
None. No names or account numbers are read. Deterministic, no AI.
"""
import re
from decimal import Decimal

from app.engine import real_bills as rb
from app.engine.photo_bills import _AMOUNT, _LEADING_DATE, _TRAILING_AMOUNTS, clean_line
from app.models.payments import Payments


def _rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


# Lines with money that are NOT payments (charges, payment plans, earlier balances, ...).
IGNORE = _rx(r"per month|/\s*month|a month\b|months?\b.*\bfor\b|pay as little|minimum payment|payment plan|"
             r"installment|billed to (insurance|plan)|total (hospital |account )?charges|^charges$|previous balance|"
             r"prior balance|past due date|statement date")
ADJUSTMENT = _rx(r"adjust|write[- ]?off|discount|contractual|allowance|financial assistance|charity|courtesy|"
                 r"reduction|savings")
INSURANCE = _rx(r"insurance (payment|paid|pmt|covered|credit)|insurance payments|(plan|insurer|insurance|medicare|"
                r"medicaid|tricare) paid|paid by (your )?(insurance|plan|insurer)|covered by (your )?(insurance|plan)|"
                r"\bins\.? (pmt|payment|paid)|(primary|secondary) (payer|insurance) payment|payer payment")
PATIENT_PAID = _rx(r"patient payment|guarantor payment|your payment|mychart payment|online payment|portal payment|"
                   r"payment.{0,20}thank you|thank you for your payment|self[- ]?pay payment|cash payment|"
                   r"check payment|(credit|debit) card payment|card payment|you paid|paid by (you|patient|guarantor)|"
                   r"patient paid|amount you paid|co-?pay (paid|collected|received)")
RESPONSIBILITY = _rx(r"patient responsibility|your responsibility|remaining responsibility|you may owe|your share|"
                     r"patient (portion|share)|member responsibility|your (total )?cost")
RESPONSIBILITY_PART = _rx(r"^(co-?pay(ment)?|co-?insurance|deductible|not covered)( amount)?$")
BALANCE = _rx(r"amount due|balance due|total due|due now|please pay|pay this amount|current balance|"
              r"account balance|new balance|you owe|remaining balance|balance remaining|outstanding balance|"
              r"patient balance|credit balance|^balance$|^total balance")
PAYMENTS_ANY = _rx(r"payments? received|total payments|payments (and|&) credits|^payments$|^credits$|"
                   r"credits applied|^payments/credits$")
PAID_OFF = _rx(r"^(paid off|paid in full|zero balance|no balance due|nothing (is )?due)\b")
SECTION = _rx(r"^(payments?|payments? (and|&) (adjustments|credits)|payment history|account activity|"
              r"transactions|payment activity)$")
INSURER = _rx(r"aetna|cigna|united ?health|\buhc\b|humana|bcbs|blue cross|blue shield|anthem|kaiser|horizon|"
              r"medicare|medicaid|tricare|oscar|ambetter|wellcare|molina|highmark|emblem|oxford|amerigroup|"
              r"caresource|insurance|health plan|\bplan\b")
SUMMARY = _rx(r"\btotal\b|payments\b|adjustments\b|credits\b|covered\b|responsibility|due\b|balance")
CREDIT_MARK = _rx(r"\b(cr|credit)\b\s*$")


def _parse(line: str) -> tuple[str, list[Decimal]] | None:
    """(description, signed amounts) for a line ending in one or more amounts."""
    credit = bool(CREDIT_MARK.search(line))
    text = CREDIT_MARK.sub("", line).strip() if credit else line
    m = _TRAILING_AMOUNTS.match(text)
    if not m:
        return None
    amounts = [rb._money(a) for a in re.findall(_AMOUNT, m["amts"])]
    amounts = [a for a in amounts if a is not None]
    if not amounts:
        return None
    if credit:
        amounts = [-abs(a) for a in amounts]
    desc = _LEADING_DATE.sub("", m["desc"]).strip(" :-|")
    return desc, amounts


def _columns(line: str) -> dict | None:
    """A table header with amount columns, e.g. 'Date Description Provider Charges Credits Balance'."""
    words = [w.strip(":").lower() for w in line.split()]
    if not any(w in rb.DESC_HEADERS for w in words):
        return None
    amounts = [w for w in words if w in rb.AMOUNT_HEADERS]
    if len(amounts) < 2 or "balance" not in amounts:
        return None
    return {"count": len(amounts), "balance": amounts.index("balance"), "last_is_balance": amounts[-1] == "balance"}


def extract_payments(pages: list[list[str]], charges: Decimal | None = None) -> Payments | None:
    """The payment summary printed on the bill, or None if it shows no payment information.
    charges (the bill's total) is used to throw away impossible amounts, e.g. a misread photo."""
    summary: dict[str, list[Decimal]] = {}
    single: dict[str, list[Decimal]] = {}
    parts: list[Decimal] = []
    balances: list[Decimal] = []
    column_balances: list[Decimal] = []
    paid_off = False
    in_section = False
    columns = None

    def add(bucket: str, desc: str, amount: Decimal):
        (summary if SUMMARY.search(desc) else single).setdefault(bucket, []).append(abs(amount))

    for page in pages:
        for raw in page:
            line = clean_line(raw)
            if not line:
                continue
            header = _columns(line)
            if header:
                columns, in_section = header, False
                continue
            parsed = _parse(line)
            if parsed is None:
                low = line.lower()
                if PAID_OFF.search(low):
                    paid_off = True
                in_section = bool(SECTION.search(low))
                continue
            desc, amounts = parsed
            amount = amounts[-1]
            if not desc or not rb._LETTERS.search(desc) or IGNORE.search(desc):
                continue
            if ADJUSTMENT.search(desc):
                add("adjustments", desc, amount)
            elif INSURANCE.search(desc):
                add("insurance_paid", desc, amount)
            elif PATIENT_PAID.search(desc):
                add("patient_paid", desc, amount)
            elif RESPONSIBILITY.search(desc):
                summary.setdefault("patient_responsibility", []).append(abs(amount))
            elif RESPONSIBILITY_PART.search(desc):
                parts.append(abs(amount))
            elif BALANCE.search(desc):
                balances.append(-abs(amount) if "credit" in desc.lower() else amount)
            elif PAYMENTS_ANY.search(desc):
                summary.setdefault("payments_any", []).append(abs(amount))
            elif in_section:   # a payer's name in a "Payments" list, e.g. "Horizon BCBS -$36,230.56"
                single.setdefault("insurance_paid" if INSURER.search(desc) else "other_payments", []).append(abs(amount))
            elif columns and len(amounts) >= 2 and not rb.SKIP_WORDS.search(desc):
                # a charge row in a table with a Balance column: its balance is part of what is still owed
                if len(amounts) == columns["count"]:
                    column_balances.append(amounts[columns["balance"]])
                elif columns["last_is_balance"]:
                    column_balances.append(amounts[-1])

    limit = charges if charges is not None and charges > 0 else None
    uncertain = False

    def pick(bucket: str) -> Decimal | None:
        nonlocal uncertain
        values = summary.get(bucket) or single.get(bucket) or []
        if limit is not None:
            ok = [v for v in values if v <= limit + Decimal("0.01")]
            uncertain = uncertain or len(ok) < len(values)
            values = ok
        if not values:
            return None
        return max(values) if bucket in summary else sum(values, Decimal("0"))

    p = Payments(insurance_paid=pick("insurance_paid"), adjustments=pick("adjustments"),
                 patient_paid=pick("patient_paid"), other_payments=pick("other_payments"))
    p.patient_responsibility = pick("patient_responsibility")
    if p.patient_responsibility is None and parts:
        total_parts = sum(parts, Decimal("0"))
        if limit is None or total_parts <= limit:
            p.patient_responsibility = total_parts
    any_paid = pick("payments_any")
    if any_paid is not None:   # "Payments received" = everyone's payments: keep only the part with no payer shown
        rest = any_paid - (p.insurance_paid or 0) - (p.patient_paid or 0) - (p.other_payments or 0)
        if rest > Decimal("0.01"):
            p.other_payments = (p.other_payments or 0) + rest
    if balances:
        p.balance_due = balances[0]
    elif column_balances:
        p.balance_due = sum(column_balances, Decimal("0"))
    elif paid_off:
        p.balance_due = Decimal("0.00")
    if p.balance_due is not None and limit is not None and abs(p.balance_due) > limit + Decimal("0.01"):
        p.balance_due, uncertain = None, True
    p.uncertain = uncertain
    return None if p.is_empty() else p