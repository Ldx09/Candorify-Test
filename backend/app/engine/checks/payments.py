"""Payment checks, for bills that show who paid what (bill.payments). Plain arithmetic, no AI.

payment_mismatch: the payments don't add up to what the bill says is still owed, either
    charges + earlier balance - insurance paid - discounts - payments = still owed, or
    the patient's share - what the patient paid = still owed.
overpaid: the patient paid more than their share, or the bill shows a credit: they may be owed a refund.
Nothing is checked when the bill doesn't show enough, or when the reader had to throw away a misread amount.
"""
from decimal import Decimal

from app.engine.models import Bill, Flag

TOLERANCE = Decimal("0.01")


def _money(x: Decimal) -> str:
    return f"${x:,.2f}"


def check_payments(bill: Bill) -> list[Flag]:
    p = bill.payments
    if p is None or p.is_empty():
        return []
    flags: list[Flag] = []
    owed = p.balance_due
    if owed is not None and not p.uncertain:
        paid_by_others = (p.insurance_paid or 0) + (p.adjustments or 0) + (p.other_payments or 0)
        if p.insurance_paid is not None or p.adjustments is not None:
            prior = p.prior_balance or 0          # an unpaid balance from an earlier visit, carried onto this bill
            expected = bill.stated_subtotal + prior - paid_by_others - (p.patient_paid or 0)
            # If the payments add up with the charges as listed, the problem is the printed total, which the
            # subtotal check already flags: don't flag the same mistake twice.
            listed = sum((ln.line_total for ln in bill.lines), Decimal("0")) + prior - paid_by_others - (p.patient_paid or 0)
            if abs(expected - owed) > TOLERANCE and abs(listed - owed) > TOLERANCE:
                steps = [f"charges {_money(bill.stated_subtotal)}"]
                plus = f" + earlier balance {_money(prior)}" if prior else ""
                for value, label in ((p.insurance_paid, "insurance paid"), (p.adjustments, "discounts"),
                                     (p.other_payments, "other payments"), (p.patient_paid, "your payments")):
                    if value is not None:
                        steps.append(f"{label} {_money(value)}")
                flags.append(Flag(
                    rule="payment_mismatch", line_no=None, code=None, expected=expected, actual=owed,
                    message=(f"The payments don't add up: {steps[0]}{plus} - {' - '.join(steps[1:])} = {_money(expected)}, but the bill "
                             f"says you owe {_money(owed)}. Ask the billing office to explain the difference."),
                ))
        elif p.patient_responsibility is not None and p.patient_paid is not None:
            expected = p.patient_responsibility - p.patient_paid
            if abs(expected - owed) > TOLERANCE:
                flags.append(Flag(
                    rule="payment_mismatch", line_no=None, code=None, expected=expected, actual=owed,
                    message=(f"The payments don't add up: your share is {_money(p.patient_responsibility)} and you "
                             f"paid {_money(p.patient_paid)}, so you should owe {_money(expected)}, but the bill says "
                             f"{_money(owed)}. Ask the billing office to explain the difference."),
                ))

    refund = None
    if p.patient_paid is not None and p.patient_responsibility is not None \
            and p.patient_paid - p.patient_responsibility > TOLERANCE:
        refund = p.patient_paid - p.patient_responsibility
        reason = (f"You paid {_money(p.patient_paid)}, but your share is {_money(p.patient_responsibility)}. "
                  f"You may be owed a refund of {_money(refund)}.")
    elif owed is not None and owed < -TOLERANCE:
        refund = -owed
        reason = f"The bill shows a credit of {_money(refund)} on your account. You may be owed a refund."
    if refund is not None:
        flags.append(Flag(rule="overpaid", line_no=None, code=None, expected=p.patient_responsibility,
                          actual=p.patient_paid, message=reason + " Ask the billing office to send it back to you."))
    return flags