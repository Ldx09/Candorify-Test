"""The totals read from the patient's insurance EOB (Explanation of Benefits). The EOB file itself is never
stored; only these amounts and the service dates are kept on the bill (bills.eob, JSON)."""
import json
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

_MONEY = dict(ge=0, max_digits=12, decimal_places=2)


class EobSummary(BaseModel):
    billed: Decimal | None = Field(default=None, **_MONEY)      # what the provider billed the insurer
    allowed: Decimal | None = Field(default=None, **_MONEY)     # the plan's approved amount
    plan_paid: Decimal | None = Field(default=None, **_MONEY)   # what the insurance paid
    you_owe: Decimal | None = Field(default=None, **_MONEY)     # what the EOB says the patient may owe
    service_dates: list[date] = Field(default_factory=list, max_length=31)

    def is_empty(self) -> bool:
        return all(v is None for v in (self.billed, self.allowed, self.plan_paid, self.you_owe))

    def to_json(self) -> str | None:
        return None if self.is_empty() else self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, raw: str | None) -> "EobSummary | None":
        if not raw:
            return None
        try:
            return cls.model_validate(json.loads(raw))
        except ValueError:
            return None