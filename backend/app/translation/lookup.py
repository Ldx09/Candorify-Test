"""Code -> plain English. Order: NLM (exact code match) -> offline fallback table -> not found.
Results from NLM are cached in memory for 24 hours so repeated codes aren't fetched again."""
import re
import time
from typing import Literal

import httpx
from pydantic import BaseModel

from app.translation import nlm
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
    source: Source


_HCPCS = re.compile(r"^[A-V]\d{4}$")                       # J2405, A6402
_ICD10 = re.compile(r"^[A-TV-Z]\d[0-9A-Z](\.?[0-9A-Z]{1,4})?$")  # R10.9, R109, S72.001A
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


def _from_fallback(c: str, system: System) -> CodeInfo:
    if c in FALLBACK_CODES:
        fb_system, desc, plain = FALLBACK_CODES[c]
        return CodeInfo(code=c, system=fb_system, description=desc, plain_english=plain, source="fallback")
    return CodeInfo(code=c, system=system, description=None, plain_english=None, source="not_found")


def lookup_code(code: str, system: System | None = None, client: httpx.Client | None = None) -> CodeInfo:
    """Resolves one code. Never raises: if NLM is down it falls back to the offline table."""
    c = normalize(code)
    system = system or classify(c)
    key = (system, c)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]

    global _nlm_down_until
    if system in nlm.TABLES and time.time() >= _nlm_down_until:
        query = _icd_with_dot(c) if system == "ICD-10-CM" else c
        try:
            rows = nlm.search(system, query, client=client)
        except nlm.NLMUnavailable:
            _nlm_down_until = time.time() + NLM_COOLDOWN_SECONDS
            return _from_fallback(c, system)  # not cached: NLM is tried again after the cooldown
        match = next((r for r in rows if normalize(r["code"]) == normalize(query)), None)
        if match:
            desc = match.get("long_desc") or match.get("name") or match.get("short_desc")
            plain = FALLBACK_CODES[c][2] if c in FALLBACK_CODES else desc
            info = CodeInfo(code=match["code"], system=system, description=desc, plain_english=plain, source="nlm")
        else:
            info = _from_fallback(c, system)
        _cache[key] = (time.time(), info)
        return info

    return _from_fallback(c, system)  # CPT / revenue codes (not in NLM), or NLM in cooldown


def clear_cache() -> None:
    global _nlm_down_until
    _cache.clear()
    _nlm_down_until = 0.0