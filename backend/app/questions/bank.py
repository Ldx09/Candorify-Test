"""Loads and checks data/question_bank.json: the fixed list of follow-up question types.
Edit questions in the JSON file; this code validates it at startup and fails loudly if something is wrong."""
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

BANK_FILE = Path(__file__).resolve().parents[2] / "data" / "question_bank.json"

CodeSystem = Literal["revenue", "cpt", "hcpcs"]
_SHAPES = {"revenue": re.compile(r"^\d{4}$"), "cpt": re.compile(r"^\d{5}$"), "hcpcs": re.compile(r"^[A-Z]\d{4}$")}


def code_system(code: str) -> CodeSystem | None:
    """4 digits = revenue code, 5 digits = CPT, a letter + 4 digits = HCPCS (Mariz's rule 1)."""
    c = code.strip().upper()
    for system, shape in _SHAPES.items():
        if shape.match(c):
            return system
    return None


class CodeRange(BaseModel):
    system: CodeSystem
    start: str = Field(alias="from")
    end: str = Field(alias="to")

    @model_validator(mode="after")
    def _valid(self):
        for c in (self.start, self.end):
            if code_system(c) != self.system:
                raise ValueError(f"'{c}' is not a valid {self.system} code")
        if self.system == "hcpcs" and self.start[0] != self.end[0]:
            raise ValueError(f"HCPCS range {self.start}-{self.end} must stay within one letter")
        if self.start > self.end:
            raise ValueError(f"Range {self.start}-{self.end} is backwards")
        return self

    def contains(self, code: str) -> bool:
        c = code.strip().upper()
        if code_system(c) != self.system:
            return False
        if self.system == "hcpcs" and c[0] != self.start[0]:
            return False
        return self.start <= c <= self.end  # same length + same letter, so text order == number order


class Check(BaseModel):
    kind: Literal["number_lower", "number_below_ratio", "answer_is"]
    value: str | None = None      # for answer_is (the English choice that creates a flag)
    ratio: Decimal | None = None  # for number_below_ratio


class QuestionType(BaseModel):
    id: str
    title: str
    priority: int                       # 1 = asked first (room / ICU nights)
    group: Literal["type", "code"]      # "type": one question adding up all matching lines; "code": one per code
    match: list[CodeRange]
    exclude: list[CodeRange] = []
    answer_type: Literal["number", "yes_no", "choice"]
    choices: list[str] | None = None    # English labels; the English label is what gets stored and compared
    text: str
    text_no_date: str | None = None
    check: Check
    flag_message: str                   # shown to the patient in the flag list
    letter_text: str                    # first-person sentence used in the dispute letter

    @model_validator(mode="after")
    def _consistent(self):
        if self.answer_type in ("yes_no", "choice") and not self.choices:
            raise ValueError(f"{self.id}: yes_no/choice questions need choices")
        if self.check.kind == "answer_is" and self.check.value not in (self.choices or []):
            raise ValueError(f"{self.id}: check value '{self.check.value}' is not one of its choices")
        if self.check.kind != "answer_is" and self.answer_type != "number":
            raise ValueError(f"{self.id}: number checks need answer_type 'number'")
        if self.check.kind == "number_below_ratio" and not self.check.ratio:
            raise ValueError(f"{self.id}: number_below_ratio needs a ratio")
        return self

    def matches(self, code: str) -> bool:
        return any(r.contains(code) for r in self.match) and not any(r.contains(code) for r in self.exclude)


class QuestionBank(BaseModel):
    max_questions: int = 5
    questions: list[QuestionType]

    @model_validator(mode="after")
    def _unique(self):
        ids = [q.id for q in self.questions]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"Duplicate question ids: {', '.join(sorted(dupes))}")
        return self

    def get(self, type_id: str) -> QuestionType | None:
        return next((q for q in self.questions if q.id == type_id), None)


def load_bank(path: Path = BANK_FILE) -> QuestionBank:
    try:
        return QuestionBank.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        raise RuntimeError(f"Question bank not found: {path}") from None
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"{path.name} is invalid: {exc}") from None


BANK = load_bank()