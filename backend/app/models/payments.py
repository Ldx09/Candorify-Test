"""Who paid what on a bill: insurance, discounts, the patient's share, the patient's payments and what is
still owed. Read from the bill when it prints these (app/engine/payments.py); every field is None when the
bill doesn't show it. Stored on the bill as JSON (bills.payments)."""
import json
from decimal import Decimal

from pydantic import BaseModel, Field

_MONEY = dict(max_digits=12, decimal_places=2)


class Payments(BaseModel):
    insurance_paid: Decimal | None = Field(default=None, ge=0, **_MONEY)          # paid by the insurance plan
    adjustments: Decimal | None = Field(default=None, ge=0, **_MONEY)             # discounts / write-offs
    patient_responsibility: Decimal | None = Field(default=None, ge=0, **_MONEY)  # the patient's share
    patient_paid: Decimal | None = Field(default=None, ge=0, **_MONEY)            # paid by the patient
    other_payments: Decimal | None = Field(default=None, ge=0, **_MONEY)          # paid, payer not shown
    prior_balance: Decimal | None = Field(default=None, ge=0, **_MONEY)           # owed from an earlier visit
    balance_due: Decimal | None = Field(default=None, **_MONEY)                   # still owed (below 0 = credit)
    uncertain: bool = False   # True if the reader had to throw away an impossible amount (not shown to users)

    def is_empty(self) -> bool:
        return all(getattr(self, f) is None for f in AMOUNT_FIELDS)

    def to_json(self) -> str | None:
        """For the database: None when the bill shows no payment information."""
        return None if self.is_empty() else self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, raw: str | None) -> "Payments | None":
        if not raw:
            return None
        try:
            return cls.model_validate(json.loads(raw))
        except ValueError:
            return None


AMOUNT_FIELDS = ("insurance_paid", "adjustments", "patient_responsibility", "patient_paid", "other_payments",
                 "prior_balance", "balance_due")