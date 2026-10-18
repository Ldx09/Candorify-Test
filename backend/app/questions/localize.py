"""Puts the follow-up questions into the user's language.

Order of preference (Mariz's question bank doc):
  1. English: the default wording, no Gemini call.
  2. Gemini rewords + translates the filled-in questions (5-second limit). Each question's reply must
     pass the checks below or that question falls back.
  3. The saved translation from data/question_bank_translations.json (made by
     scripts/translate_question_bank.py).
  4. The default English wording.

Checks on Gemini's reply: same question ids in the same order; the same numbers as the English text
and no new ones; under 2x the English length; the same number of choice labels.
Only the filled-in question text goes to Gemini: no name, account number or other personal details.
Answer values stay English (choices carry value + label), so the answer check never depends on Gemini.
"""
import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.models.line_item import format_qty
from app.questions.bank import BANK
from app.questions.picker import Question
from app.schemas.questions import ChoiceOut, QuestionOut
from app.translation import gemini_client
from app.translation.languages import Language, get_language
from app.translation.translator import FALLBACK_NOTE, OFFICIAL_NOTE, _digits

logger = logging.getLogger("candorify.questions")

TRANSLATIONS_FILE = Path(__file__).resolve().parents[2] / "data" / "question_bank_translations.json"
GEMINI_TIMEOUT_SECONDS = 5.0
MAX_LENGTH_RATIO = 2

_cache: dict[tuple[str, str], tuple[str, list[str] | None]] = {}


class Localized(BaseModel):
    questions: list[QuestionOut]
    language: str
    rtl: bool
    note: str | None = None


@lru_cache(maxsize=1)
def saved_translations() -> dict:
    try:
        return json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8")).get("languages", {})
    except (FileNotFoundError, ValueError):
        return {}


def _english(q: Question) -> QuestionOut:
    return QuestionOut(id=q.id, type=q.type, text=q.text, answer_type=q.answer_type,
                       choices=[ChoiceOut(value=c, label=c) for c in q.choices] if q.choices else None,
                       line_refs=q.line_refs, translated=False)


def _fill(template: str, q: Question) -> str:
    values = dict(qty=format_qty(q.billed_qty), description=q.description, date=q.date or "",
                  minutes=q.minutes if q.minutes is not None else "")
    for k, v in values.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def _from_saved(q: Question, lang: str) -> QuestionOut | None:
    entry = saved_translations().get(lang, {})
    t = entry.get("types", {}).get(q.type, {})
    qt = BANK.get(q.type)
    use_no_date = not q.date and qt.text_no_date
    template = (t.get("text_no_date") if use_no_date else t.get("text")) or {}
    if not template.get("text"):
        return None
    labels = None
    if q.choices:
        saved = entry.get("choices", {})
        labels = [(saved.get(c) or {}).get("text") or c for c in q.choices]
    out = _english(q)
    out.text = _fill(template["text"], q)
    if labels:
        out.choices = [ChoiceOut(value=c, label=lbl) for c, lbl in zip(q.choices, labels)]
    out.translated = True
    return out


def _prompt(items: list[dict], lang: Language) -> str:
    return (
        f"You help patients check their hospital bill. Rewrite each question below in {lang.name} so it is "
        "short, friendly and easy to understand for someone with no medical background.\n"
        "Rules:\n"
        "- Keep the meaning exactly the same. Do not add or remove facts.\n"
        "- Keep every number, date and billing code exactly as written. Do not add any new numbers.\n"
        "- Keep the answer choices in the same order and translate them too.\n"
        "- Keep each question about as long as the original (never more than twice as long).\n"
        'Reply with JSON only in this shape: {"questions": [{"id": "...", "text": "...", "choices": ["..."]}]} '
        "with the same ids in the same order.\n\n"
        f"{json.dumps({'questions': items}, ensure_ascii=False)}"
    )


def _cache_key(lang: str, q: Question) -> tuple[str, str]:
    raw = json.dumps([q.text, q.choices], ensure_ascii=False)
    return lang, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _passes(q: Question, text, choices) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    if len(text) > MAX_LENGTH_RATIO * len(q.text):
        return False
    if _digits(text) != _digits(q.text):
        return False
    if q.choices:
        if not isinstance(choices, list) or len(choices) != len(q.choices) or \
                not all(isinstance(c, str) and c.strip() for c in choices):
            return False
        if any(_digits(c) != _digits(e) for c, e in zip(choices, q.choices)):
            return False
    return True


def _from_gemini(questions: list[Question], lang: Language, client: httpx.Client | None) -> dict[str, QuestionOut]:
    out: dict[str, QuestionOut] = {}
    todo = []
    for q in questions:
        hit = _cache.get(_cache_key(lang.code, q))
        if hit:
            out[q.id] = _build(q, *hit)
        else:
            todo.append(q)
    if not todo:
        return out
    items = [{"id": q.id, "text": q.text, **({"choices": q.choices} if q.choices else {})} for q in todo]
    try:
        reply = gemini_client.generate_json(_prompt(items, lang), client=client,
                                            timeout=GEMINI_TIMEOUT_SECONDS, retries=0)
    except gemini_client.GeminiUnavailable as exc:
        logger.warning("Question translation unavailable (%s)", exc)
        return out
    got = reply.get("questions")
    if not isinstance(got, list) or [g.get("id") if isinstance(g, dict) else None for g in got] != [q.id for q in todo]:
        logger.warning("Gemini changed the question ids or order; not using its reply")
        return out
    for q, g in zip(todo, got):
        if _passes(q, g.get("text"), g.get("choices")):
            _cache[_cache_key(lang.code, q)] = (g["text"].strip(), [c.strip() for c in g["choices"]] if q.choices else None)
            out[q.id] = _build(q, *_cache[_cache_key(lang.code, q)])
        else:
            logger.warning("Gemini wording for %s failed a check; using fallback", q.id)
    return out


def _build(q: Question, text: str, labels: list[str] | None) -> QuestionOut:
    out = _english(q)
    out.text = text
    if labels:
        out.choices = [ChoiceOut(value=c, label=lbl) for c, lbl in zip(q.choices, labels)]
    out.translated = True
    return out


def localize_questions(questions: list[Question], language: str | None,
                       client: httpx.Client | None = None) -> Localized:
    lang = get_language(language or "en")
    if lang is None:
        raise ValueError(f"Unsupported language '{language}'")
    if lang.code == "en" or not questions:
        return Localized(questions=[_english(q) for q in questions], language=lang.code, rtl=lang.rtl)
    gemini = _from_gemini(questions, lang, client)
    result = []
    for q in questions:
        result.append(gemini.get(q.id) or _from_saved(q, lang.code) or _english(q))
    done = sum(r.translated for r in result)
    if done == len(result):
        note = OFFICIAL_NOTE
    elif done:
        note = OFFICIAL_NOTE + " Some parts couldn't be translated and are shown in English."
    else:
        note = FALLBACK_NOTE
    return Localized(questions=result, language=lang.code, rtl=lang.rtl, note=note)


def clear_cache() -> None:
    _cache.clear()
    saved_translations.cache_clear()