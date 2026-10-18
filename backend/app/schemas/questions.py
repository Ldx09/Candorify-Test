"""Shapes for the follow-up questions and the answers the patient sends back."""
from pydantic import BaseModel, Field

from app.engine.models import FlagReport
from app.schemas.bills import BillOut


class ChoiceOut(BaseModel):
    value: str   # send THIS back as the answer (always English, e.g. "No")
    label: str   # show this to the user (their language)


class QuestionOut(BaseModel):
    id: str                       # send back as question_id
    type: str
    text: str                     # in the user's language when available
    answer_type: str              # number | yes_no | choice
    choices: list[ChoiceOut] | None = None
    line_refs: list[int]          # bill lines this question is about
    translated: bool = False      # False = shown in English


class QuestionsOut(BaseModel):
    bill_id: int
    questions: list[QuestionOut]
    answers: dict[str, str | None] = Field(default_factory=dict)  # answers already saved, by question_id
    language: str = "en"
    rtl: bool = False
    translation_note: str | None = None


class UploadResult(BaseModel):
    bill: BillOut
    flags: FlagReport
    questions: list[QuestionOut]
    language: str = "en"
    rtl: bool = False
    translation_note: str | None = None


class AnswerIn(BaseModel):
    question_id: str = Field(min_length=1, max_length=80)
    value: bool | int | float | str | None = None  # number, "Yes"/"No"/"Not sure", a choice value, or null = skipped


class ReviewIn(BaseModel):
    bill_id: int
    answers: list[AnswerIn] = Field(max_length=20)


class ReviewResult(BaseModel):
    bill_id: int
    answers_saved: int
    new_flag_ids: list[int]   # answer_mismatch flags created by this review
    flags: FlagReport         # every flag on the bill (engine + answers)