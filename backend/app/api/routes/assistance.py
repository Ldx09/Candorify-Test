"""Financial assistance checker. Public, and nothing is stored or logged: the income is used once.

    POST /api/assistance/check
    {"household_size": 3, "yearly_income": 42000, "state": "NJ",
     "insured": true, "amount": 550, "hospital": "Sample Hospital", "date_of_service": "09/12/2026"}
Only household_size and yearly_income are required.
"""
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from app.engine import assistance

router = APIRouter(prefix="/api/assistance", tags=["assistance"])


class AssistanceIn(BaseModel):
    household_size: int = Field(ge=1, le=20)
    yearly_income: Decimal = Field(ge=0, le=10_000_000, max_digits=10, decimal_places=2)
    state: str | None = Field(default=None, max_length=2)
    insured: bool | None = None                      # None = didn't say
    amount: Decimal | None = Field(default=None, ge=0, le=10_000_000, max_digits=10, decimal_places=2)
    hospital: str | None = Field(default=None, max_length=120)
    date_of_service: str | None = Field(default=None, max_length=20)

    @field_validator("state")
    @classmethod
    def _state(cls, v):
        if v in (None, ""):
            return None
        if v.upper() not in assistance.US_STATES:
            raise ValueError("Use a two-letter US state code, like NJ")
        return v.upper()


class Savings(BaseModel):
    asked: Decimal
    may_pay: Decimal | None = None
    text: str


class Medicaid(BaseModel):
    likely: bool
    text: str


class StateProgram(BaseModel):
    name: str
    summary: str
    applies: bool
    note: str | None = None
    source: str


class PaymentPlan(BaseModel):
    monthly: Decimal
    legal_cap: bool          # True when it's the state's legal limit, False when it's our suggestion
    text: str


class AssistanceOut(BaseModel):
    tier: str                # "free" | "discount" | "ask"
    headline: str
    guaranteed: bool         # True when a state law covers this income (not just hospital policy)
    percent_of_poverty: int
    poverty_line: int
    guideline_year: int
    state: str | None
    savings: Savings | None
    medicaid: Medicaid | None
    state_program: StateProgram | None
    payment_plan: PaymentPlan | None
    details: list[str]
    rights: list[str]
    next_steps: list[str]
    deadline: str
    letter_subject: str
    letter: str
    more_info: str


@router.post("/check", response_model=AssistanceOut)
def check(body: AssistanceIn):
    return assistance.check(body.household_size, body.yearly_income, body.state, insured=body.insured,
                            amount=body.amount, hospital=body.hospital, date_of_service=body.date_of_service)