"""Translates text the user reads (questions, code explanations, letter copies) into their language.

Safety rules (translation must never change what the bill says):
  * English stays the official version; translations are read-only copies.
  * Every number and money amount must survive unchanged. If Gemini drops or changes one, that text
    is shown in English instead.
  * Personal details (the patient's name, address, account number) are replaced with placeholders
    before anything is sent to Gemini and put back afterwards.
  * If Gemini is unavailable (no key, outage, bad reply), the English text is returned. Never an error.
Successful translations are cached in memory so the same text isn't translated (and paid for) twice.
"""
import hashlib
import json
import logging
import re
import unicodedata

import httpx
from pydantic import BaseModel

from app.translation import gemini_client
from app.translation.languages import Language, get_language

logger = logging.getLogger("candorify.translation")

OFFICIAL_NOTE = "Translated automatically for your convenience. The English version is the official one."
FALLBACK_NOTE = "Translation isn't available right now, so this is shown in English."

_cache: dict[tuple[str, str], str] = {}
_NUMBER = re.compile(r"\d+(?:[.,\u066B\u066C]\d+)*")  # \d also matches Arabic-Indic and other digits


class TranslatedItem(BaseModel):
    source: str
    text: str
    translated: bool  # False = shown in English (not needed, unavailable, or failed a safety check)


class TranslationResult(BaseModel):
    language: Language
    items: list[TranslatedItem]
    note: str | None = None


def _digits(text: str) -> list[str]:
    """All numbers in the text as plain ASCII digit strings ("$1,450.00" -> "145000"), sorted."""
    found = []
    for m in _NUMBER.finditer(text):
        found.append("".join(str(unicodedata.digit(ch)) for ch in m.group() if unicodedata.digit(ch, None) is not None))
    return sorted(found)


def _mask(text: str, protect: list[str]) -> tuple[str, dict[str, str]]:
    tokens: dict[str, str] = {}
    for i, value in enumerate(sorted({p for p in protect if p and p.strip()}, key=len, reverse=True), start=1):
        if value in text:
            token = f"[[P{i}]]"
            tokens[token] = value
            text = text.replace(value, token)
    return text, tokens


def _unmask(text: str, tokens: dict[str, str]) -> str:
    for token, value in tokens.items():
        text = text.replace(token, value)
    return text


def _prompt(texts: list[str], lang: Language) -> str:
    return (
        f"Translate each string in the JSON array below from English into {lang.name}.\n"
        "This is for a patient reading their medical bill. Use simple, plain wording.\n"
        "Rules:\n"
        "- Keep every number, money amount, date and billing code (like 99284, J2405, 0250) exactly as written.\n"
        "- Keep placeholders like [[P1]] exactly as written.\n"
        "- Keep line breaks.\n"
        "- Translate only; do not add, remove or explain anything.\n"
        'Reply with JSON only, in this shape: {"translations": ["...", "..."]} with exactly one entry per input, '
        "in the same order.\n\n"
        f"{json.dumps(texts, ensure_ascii=False)}"
    )


def _key(lang: str, text: str) -> tuple[str, str]:
    return (lang, hashlib.sha256(text.encode("utf-8")).hexdigest())


def translate_texts(texts: list[str], language_code: str, protect: list[str] | None = None,
                    client: httpx.Client | None = None) -> TranslationResult:
    """Translates a list of texts. Never raises for Gemini problems: falls back to English."""
    lang = get_language(language_code)
    if lang is None:
        raise ValueError(f"Unsupported language '{language_code}'")
    if lang.code == "en" or not texts:
        return TranslationResult(language=lang, items=[TranslatedItem(source=t, text=t, translated=False) for t in texts])

    masked = [_mask(t, protect or []) for t in texts]
    results: list[str | None] = [None] * len(texts)
    todo = []
    for i, (m, _) in enumerate(masked):
        hit = _cache.get(_key(lang.code, m))
        if hit is not None:
            results[i] = hit
        elif m.strip():
            todo.append(i)
        else:
            results[i] = m

    failed = False
    if todo:
        try:
            reply = gemini_client.generate_json(_prompt([masked[i][0] for i in todo], lang), client=client)
            out = reply.get("translations")
            if not isinstance(out, list) or len(out) != len(todo) or not all(isinstance(x, str) for x in out):
                raise gemini_client.GeminiUnavailable("wrong number of translations")
            for i, t in zip(todo, out):
                src = masked[i][0]
                tokens_ok = all(tok in t for tok in masked[i][1])
                if t.strip() and tokens_ok and _digits(t) == _digits(src):
                    results[i] = t
                    _cache[_key(lang.code, src)] = t
                else:
                    logger.warning("Translation to %s rejected by safety check; showing English", lang.code)
        except gemini_client.GeminiUnavailable as exc:
            failed = True
            logger.warning("Translation unavailable (%s); showing English", exc)

    items = []
    for i, original in enumerate(texts):
        if results[i] is None:
            items.append(TranslatedItem(source=original, text=original, translated=False))
        else:
            items.append(TranslatedItem(source=original, text=_unmask(results[i], masked[i][1]),
                                        translated=results[i] != masked[i][0] or not masked[i][0].strip()))
    any_ok = any(it.translated for it in items)
    note = OFFICIAL_NOTE if any_ok else FALLBACK_NOTE
    if any_ok and (failed or not all(it.translated for it in items if it.source.strip())):
        note = OFFICIAL_NOTE + " Some parts couldn't be translated and are shown in English."
    return TranslationResult(language=lang, items=items, note=note)


def clear_cache() -> None:
    _cache.clear()