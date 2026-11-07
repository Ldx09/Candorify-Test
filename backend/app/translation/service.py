"""Translation service: the one entry point for code -> plain English.

Order: cache -> NLM API (exact code match) -> offline dictionary (data/medical_codes.json) -> not found.
NLM results are cached in memory for 24 hours. Every result says where it came from (`source`)
and whether it was served from the cache (`cached`), so the frontend can be transparent about it."""
import re
import time
from typing import Literal

import httpx
from pydantic import BaseModel

from app.translation import nlm_client as nlm
from app.translation.fallback import FALLBACK_CODES

System = Literal["HCPCS", "ICD-10-CM", "CPT", "Revenue code", "unknown"]
Source = Literal["nlm", "fallback", "not_found"]

CACHE_SECONDS = 24 * 60 * 60
NLM_COOLDOWN_SECONDS = 60  # after NLM fails, use the fallback table for this long before trying NLM again
_cache: dict[tuple[str, str], tuple[float, "CodeInfo"]] = {}
_nlm_down_until = 0.0


class CodeInfo(BaseModel):
    code: str
    system: System
    description: str | None      # official description
    plain_english: str | None    # simpler wording when we have it, otherwise the official description
    source: Source               # nlm = live NLM API, fallback = offline dictionary, not_found = neither had it
    cached: bool = False         # True when this answer came from the cache instead of a fresh lookup
    message: str | None = None   # only when not_found: what the user can do next (shown instead of a description)


_NOTED = " We've noted this code so we can add it."
NOT_FOUND_MESSAGES = {
    "CPT": ("We don't have this CPT code in our list yet. CPT descriptions are licensed by the American Medical "
            "Association, so we can't look up every one. Ask your provider's billing office what this charge was "
            "for, or include it in your letter." + _NOTED),
    "HCPCS": ("We couldn't find this HCPCS code. Check it's typed exactly as on your bill (a letter and 4 numbers). "
              "If it's right, ask your provider's billing office what it was for." + _NOTED),
    "ICD-10-CM": ("We couldn't find this diagnosis code. Check it's typed exactly as on your bill, including the dot "
                  "(like R10.9). If it's right, ask your provider what it means." + _NOTED),
    "Revenue code": ("We don't have this revenue code in our list yet. Ask your provider's billing office what this "
                     "charge was for." + _NOTED),
    "unknown": ("This doesn't look like a billing code. CPT codes are 5 numbers (like 99284), HCPCS codes are a "
                "letter and 4 numbers (like J2405), and diagnosis codes look like R10.9."),
}
OFFLINE_MESSAGE = ("We couldn't reach the medical code database right now, and this code isn't in our offline list. "
                   "Please try again in a minute.")


_HCPCS = re.compile(r"^[A-CEGHJ-MP-TV]\d{4}$")             # J2405, A6402 (HCPCS Level II letters only)
_ICD10 = re.compile(r"^[A-Z]\d[0-9A-Z](\.?[0-9A-Z]{1,4})?$")    # R10.9, R109, S72.001A, U07.1
_CPT = re.compile(r"^\d{4}[0-9A-Z]$")                       # 99284, 0001U
_REVENUE = re.compile(r"^\d{4}$")                           # 0250


def normalize(code: str) -> str:
    return code.strip().upper()


def classify(code: str) -> System:
    """Guesses the code system from the code's shape."""
    c = normalize(code)
    if "." in c and _ICD10.match(c):
        return "ICD-10-CM"
    if _HCPCS.match(c):
        return "HCPCS"
    if _CPT.match(c):
        return "CPT"
    if _REVENUE.match(c):
        return "Revenue code"
    if _ICD10.match(c):
        return "ICD-10-CM"
    return "unknown"


def _icd_with_dot(c: str) -> str:
    """NLM stores ICD-10-CM codes with a dot after the 3rd character (R109 -> R10.9)."""
    return c if "." in c or len(c) <= 3 else f"{c[:3]}.{c[3:]}"


_SHAPES = {"HCPCS": _HCPCS, "ICD-10-CM": _ICD10, "CPT": _CPT, "Revenue code": _REVENUE}


def _fits(system: System, c: str) -> bool:
    """True when the code has the right shape for that code system."""
    shape = _SHAPES.get(system)
    return bool(shape and shape.match(c))


def _fallback_key(c: str) -> str | None:
    """The offline dictionary stores ICD-10-CM codes with their dot (R10.9); accept R109 too."""
    for key in (c, _icd_with_dot(c)):
        if key in FALLBACK_CODES:
            return key
    return None


def _from_fallback(c: str, system: System, provider_down: bool = False) -> CodeInfo:
    key = _fallback_key(c)
    if key:
        fb_system, desc, plain = FALLBACK_CODES[key]
        return CodeInfo(code=key, system=fb_system, description=desc, plain_english=plain, source="fallback")
    message = OFFLINE_MESSAGE if provider_down else NOT_FOUND_MESSAGES[system]
    return CodeInfo(code=c, system=system, description=None, plain_english=None, source="not_found", message=message)


def lookup_code(code: str, system: System | None = None, client: httpx.Client | None = None) -> CodeInfo:
    """Resolves one code. Never raises: if NLM is down it falls back to the offline table."""
    c = normalize(code)
    guessed = classify(c)
    if system is None or (not _fits(system, c) and guessed != "unknown"):
        system = guessed  # e.g. "R10.9" sent with type CPT: use the type the code's shape says
    key = (system, c)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1].model_copy(update={"cached": True})

    global _nlm_down_until
    if system in nlm.TABLES and time.time() >= _nlm_down_until:
        query = _icd_with_dot(c) if system == "ICD-10-CM" else c
        try:
            rows = nlm.search(system, query, client=client)
        except nlm.ProviderUnavailable:
            _nlm_down_until = time.time() + NLM_COOLDOWN_SECONDS
            return _from_fallback(c, system, provider_down=True)  # not cached: NLM is tried again after the cooldown
        match = next((r for r in rows if normalize(r["code"]) == normalize(query)), None)
        if match:
            desc = match.get("long_desc") or match.get("name") or match.get("short_desc")
            fb = _fallback_key(c)
            plain = FALLBACK_CODES[fb][2] if fb else desc
            info = CodeInfo(code=match["code"], system=system, description=desc, plain_english=plain, source="nlm")
        else:
            info = _from_fallback(c, system)
        _cache[key] = (time.time(), info)
        return info

    # CPT / revenue codes (not in NLM), or NLM in its cooldown after a failure
    return _from_fallback(c, system, provider_down=system in nlm.TABLES)


def clear_cache() -> None:
    global _nlm_down_until
    _cache.clear()
    _nlm_down_until = 0.0