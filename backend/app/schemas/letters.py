from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.letters.generate import LetterDetails


class FlagSelector(BaseModel):
    rule: Literal["duplicate_line", "line_math", "subtotal_mismatch"]
    line_no: int | None = None  # None for the subtotal flag


class LetterRequest(LetterDetails):
    """Body for POST /api/letters. Patient/provider details are optional: blanks become [placeholders]."""
    bill_id: int
    letter_type: Literal["request", "dispute"]
    # Dispute only: which of the engine's flags the patient confirmed. Leave empty to include every flag.
    flags: list[FlagSelector] = Field(default_factory=list)

    @model_validator(mode="after")
    def _flags_only_for_dispute(self):
        if self.flags and self.letter_type != "dispute":
            raise ValueError("flags can only be sent with letter_type 'dispute'")
        return self


class LetterOut(BaseModel):
    letter_type: Literal["request", "dispute"]
    bill_id: int
    text: str
    flag_count: int = 0
    flagged_lines: list[int] = Field(default_factory=list)  # bill lines the dispute letter questions