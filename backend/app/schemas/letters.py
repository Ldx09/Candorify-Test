from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.letters.generate import LetterDetails
from app.schemas.translation import check_language


class FlagSelector(BaseModel):
    rule: Literal["duplicate_line", "line_math", "subtotal_mismatch"]
    line_no: int | None = None  # None for the subtotal flag


class LetterRequest(LetterDetails):
    """Body for POST /api/letters. Patient/provider details are optional: blanks become [placeholders]."""
    bill_id: int
    letter_type: Literal["request", "dispute"]
    # Dispute only. Which flags go in the letter, in order of preference:
    #   flag_ids -> exactly these flags;  flags -> by rule + line;
    #   neither  -> flags with status "add_to_letter", or if none are marked, every flag not "dismissed".
    flag_ids: list[int] = Field(default_factory=list)
    flags: list[FlagSelector] = Field(default_factory=list)
    # Optional: also return a read-only copy in this language. The letter itself is always English.
    language: str | None = Field(default=None, max_length=10)

    _lang = field_validator("language")(check_language)

    @model_validator(mode="after")
    def _flags_only_for_dispute(self):
        if (self.flags or self.flag_ids) and self.letter_type != "dispute":
            raise ValueError("flags can only be sent with letter_type 'dispute'")
        return self


class LetterOut(BaseModel):
    letter_type: Literal["request", "dispute"]
    bill_id: int
    text: str
    flag_count: int = 0
    flagged_lines: list[int] = Field(default_factory=list)  # bill lines the dispute letter questions
    flag_ids: list[int] = Field(default_factory=list)       # the flags included in the letter
    translation: "LetterTranslation | None" = None          # read-only copy, only if `language` was sent


class LetterTranslation(BaseModel):
    language: str
    language_name: str
    rtl: bool
    text: str          # the letter in the user's language (or English if translation wasn't possible)
    translated: bool
    note: str          # "The English version is the official one" etc.


LetterOut.model_rebuild()