from pydantic import BaseModel, Field, field_validator

from app.translation.languages import get_language
from app.translation.translator import TranslationResult  # noqa: F401  (response model)


def check_language(v: str | None) -> str | None:
    if v is not None and get_language(v) is None:
        raise ValueError(f"Unsupported language '{v}'. See GET /api/languages for the list")
    return v


class TextTranslationRequest(BaseModel):
    language: str = Field(min_length=2, max_length=10)
    texts: list[str] = Field(min_length=1, max_length=50)

    _lang = field_validator("language")(check_language)

    @field_validator("texts")
    @classmethod
    def _text_length(cls, v: list[str]) -> list[str]:
        if any(len(t) > 5000 for t in v):
            raise ValueError("Each text can be at most 5000 characters")
        return v