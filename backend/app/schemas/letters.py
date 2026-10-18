from typing import Literal

from pydantic import BaseModel, Field

from app.letters.generator import LetterDetails


class FlagSelector(BaseModel):
    rule: Literal["duplicate_line", "line_math", "subtotal_mismatch"]
    line_no: int | None = None  # None for the subtotal flag


class DisputeLetterRequest(LetterDetails):
    # Which of the engine's flags the patient confirmed. Leave empty to include every flag.
    flags: list[FlagSelector] = Field(default_factory=list)


class LetterOut(BaseModel):
    letter_type: Literal["request", "dispute"]
    bill_id: int
    text: str
    flag_count: int = 0