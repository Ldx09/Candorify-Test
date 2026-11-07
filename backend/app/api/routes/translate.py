"""Code explanations and translation.
  GET  /api/translate?code=      code -> plain English (cache -> NLM -> offline dictionary). Protected.
  POST /api/translate/text       translate texts the user reads into their language (Gemini). Protected.
  GET  /api/languages            languages the user can pick. Public (the sign-in page can show it).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.translation import TextTranslationRequest, TranslationResult
from app.services.missing_codes import record_missing
from app.translation.languages import LANGUAGES, Language
from app.translation.service import CodeInfo, System, lookup_code
from app.translation.translator import translate_texts

router = APIRouter(tags=["translate"])
public_router = APIRouter(prefix="/api", tags=["translate"])


@router.get("/translate", response_model=CodeInfo)
def translate(
    code: str = Query(min_length=1, max_length=20, description="Billing or diagnosis code, e.g. J2405, 99284, R10.9"),
    system: System | None = Query(default=None, description="Optional: force the code system"),
    db: Session = Depends(get_db),
):
    """Looks up the code: cache -> NLM -> offline dictionary.
    `source` says where the answer came from (nlm / fallback / not_found); `cached` is true for cache hits.
    When nothing is found, `message` says what the user can do next, and the code is counted in
    `missing_codes` so we know which codes to add."""
    info = lookup_code(code, system=system)
    record_missing(db, info)
    return info


@router.post("/translate/text", response_model=TranslationResult)
def translate_text(body: TextTranslationRequest):
    """Translates up to 50 texts (questions, explanations...) into the user's language.
    Each item says whether it was translated; anything that can't be translated safely comes back in English."""
    return translate_texts(body.texts, body.language)


@public_router.get("/languages", response_model=list[Language])
def languages():
    """Languages users can choose. `rtl: true` means the page should be shown right-to-left."""
    return LANGUAGES