"""EOB checks: compares the bill with the patient's insurance EOB (bill.eob). Plain arithmetic, no AI.

eob_owe_mismatch:   the bill asks for MORE than the EOB says the patient may owe (the most useful catch).
eob_paid_mismatch:  the insurance payment on the bill differs from what the EOB says the plan paid.
eob_billed_mismatch: the bill's total differs from what the EOB says was billed.
Nothing is compared when the EOB's service dates don't include the bill's date of service (another visit).
Differences under $1 are ignored (rounding).
"""
from decimal import Decimal

from app.engine.models import Bill, Flag

TOLERANCE = Decimal("1.00")


def _money(x: Decimal) -> str:
    return f"${x:,.2f}"


def same_visit(bill: Bill) -> bool | None:
    """True/False when both the bill and the EOB show service dates; None when we can't tell."""
    e = bill.eob
    if e is None or not e.service_dates or bill.date_of_service is None:
        return None
    return bill.date_of_service in e.service_dates


def asked_of_patient(bill: Bill) -> Decimal | None:
    """What the bill asks the patient to pay in total (their share), from the bill's payment section."""
    p = bill.payments
    if p is None:
        return None
    if p.patient_responsibility is not None:
        return p.patient_responsibility
    if p.balance_due is not None and p.balance_due >= 0:
        return p.balance_due + (p.patient_paid or 0)
    return None


def check_eob(bill: Bill) -> list[Flag]:
    e = bill.eob
    if e is None or e.is_empty() or same_visit(bill) is False:
        return []
    flags: list[Flag] = []
    asked = asked_of_patient(bill)
    if e.you_owe is not None and asked is not None and asked - e.you_owe > TOLERANCE:
        flags.append(Flag(
            rule="eob_owe_mismatch", line_no=None, code=None, expected=e.you_owe, actual=asked,
            message=(f"Your insurance EOB says you may owe {_money(e.you_owe)} for this visit, but the bill asks you to "
                     f"pay {_money(asked)} ({_money(asked - e.you_owe)} more). Ask the billing office to bill you only "
                     f"what your EOB shows."),
        ))
    p = bill.payments
    if e.plan_paid is not None and p is not None and p.insurance_paid is not None \
            and abs(e.plan_paid - p.insurance_paid) > TOLERANCE:
        flags.append(Flag(
            rule="eob_paid_mismatch", line_no=None, code=None, expected=e.plan_paid, actual=p.insurance_paid,
            message=(f"Your insurance EOB says your plan paid {_money(e.plan_paid)}, but the bill shows insurance paid "
                     f"{_money(p.insurance_paid)}. Ask the billing office to check that your insurance payment was "
                     f"applied correctly."),
        ))
    if e.billed is not None and abs(e.billed - bill.stated_subtotal) > TOLERANCE:
        flags.append(Flag(
            rule="eob_billed_mismatch", line_no=None, code=None, expected=e.billed, actual=bill.stated_subtotal,
            message=(f"Your insurance EOB lists {_money(e.billed)} billed for this visit, but the bill's total is "
                     f"{_money(bill.stated_subtotal)}. The bill may include charges your insurance never saw, or the "
                     f"EOB may cover only part of the visit. Ask the billing office to explain the difference."),
        ))
    return flags
