"""Fixes billing codes that the phone misread ("AB402" for A6402, "94284" for 99284, "2120" for 0120).

A code is kept when it is in our code list, or when it looks like a real code and nothing better fits
(real bills have many codes we don't list). A misread code is replaced only by a listed code that is one or
two characters away AND whose description shares words with the charge's description, so a code is never
made up. When the printed code is unreadable, the description is used (code_matching.match_code), and as a
last resort a listed code whose description clearly matches the charge. Deterministic, no AI.
"""
import re
from functools import lru_cache

from app.engine.code_matching import match_code

# Characters a phone often reads in place of others, both ways.
_LOOKS_LIKE = {"0": "OoDQ", "1": "IlLi|", "2": "Z", "5": "S", "6": "Gb", "8": "B", "9": "g",
               "O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "G": "6", "B": "86"}
_WELL_FORMED = re.compile(r"^(\d{5}|[A-V]\d{4}|0\d{3})$")       # CPT, HCPCS, revenue code
_WORD = re.compile(r"[a-z]{4,}")
_STOP = {"with", "without", "each", "other", "than", "general", "per", "patient", "service", "services", "level"}


@lru_cache(maxsize=1)
def _codes() -> dict[str, set[str]]:
    """code -> words in its description (official + plain English)."""
    from app.translation.fallback import FALLBACK_CODES
    return {code: _words(desc + " " + plain) for code, (_, desc, plain) in FALLBACK_CODES.items()}


def _words(text: str) -> set[str]:
    return {w[:6] for w in _WORD.findall(text.lower()) if w not in _STOP}   # first 6 letters: "dressing"~"dressings"


def _distance(a: str, b: str) -> int:
    """Characters that differ, not counting look-alike swaps (B/8, O/0, ...)."""
    if len(a) != len(b):
        return 9
    return sum(1 for x, y in zip(a, b) if x != y and x not in _LOOKS_LIKE.get(y, "") and y not in _LOOKS_LIKE.get(x, ""))


def _changes(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y) if len(a) == len(b) else 9


def _best_by_description(candidates: list[str], description: str, need: int = 1) -> str:
    words = _words(description)
    scored = sorted(((len(words & _codes()[c]), c) for c in candidates), reverse=True)
    if scored and scored[0][0] >= need and (len(scored) == 1 or scored[0][0] > scored[1][0]):
        return scored[0][1]
    return ""


def fix_code(code: str, description: str, garbled: bool = False) -> str:
    """The best code for a charge read from a photo, or "" when there is no clear one."""
    code = (code or "").strip().upper()
    known = _codes()
    if code in known:
        return code
    if code:
        # one or two characters off (look-alike characters count less), and the descriptions agree
        near = [c for c in known if _changes(code, c) <= 2 and _distance(code, c) <= 1]
        if len(code) == 4 and code.isdigit():                      # "2120" for revenue code "0120"
            near += [c for c in known if len(c) == 4 and c[1:] == code[1:]]
        if len(code) == 5 and code[0].isdigit():                   # "42405" for HCPCS "J2405"
            near += [c for c in known if len(c) == 5 and c[1:] == code[1:] and not c[0].isdigit()]
        # one character dropped ("A402" for A6402) or added
        near += [c for c in known if len(c) == len(code) + 1 and any(c[:i] + c[i + 1:] == code for i in range(len(c)))]
        near += [c for c in known if len(c) == len(code) - 1 and any(code[:i] + code[i + 1:] == c for i in range(len(code)))]
        best = _best_by_description(sorted(set(near)), description)
        if best:
            return best
        if _WELL_FORMED.match(code):
            return code                                            # a real code we just don't list
    matched = match_code(description)
    if matched:
        return matched
    if garbled or code:                                            # something was printed there: match by words
        return _best_by_description(list(known), description, need=2)
    return ""