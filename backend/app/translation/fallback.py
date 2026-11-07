"""Offline dictionary of common codes, loaded from backend/data/medical_codes.json,
backend/data/cpt_codes.json (500+ common CPT codes, described in our own plain words) and
backend/data/revenue_codes.json (more hospital department codes, used by real summary bills).
Used when the NLM API is unavailable (ProviderUnavailable) or doesn't cover the code.
NLM has HCPCS and ICD-10-CM only; CPT codes (licensed by the AMA) and hospital revenue codes
are not in NLM, so for those this dictionary is the main source.

To add a code, add an entry to either file (CPT codes go in cpt_codes.json):
    "99284": {"system": "CPT", "description": "...", "plain_english": "..."}
A code may only appear once across both files.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MEDICAL_CODES_FILE = DATA_DIR / "medical_codes.json"
CPT_CODES_FILE = DATA_DIR / "cpt_codes.json"
REVENUE_CODES_FILE = DATA_DIR / "revenue_codes.json"   # extra hospital department codes (real summary bills)
VALID_SYSTEMS = {"HCPCS", "ICD-10-CM", "CPT", "Revenue code"}


def _load(path: Path) -> dict[str, tuple[str, str, str]]:
    """Reads and checks the file. Any mistake stops the server at startup with a clear message."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError(f"Offline code dictionary not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path.name} is not valid JSON (line {exc.lineno}): {exc.msg}") from None

    codes: dict[str, tuple[str, str, str]] = {}
    for code, entry in raw.items():
        key = code.strip().upper()
        missing = [f for f in ("system", "description", "plain_english") if not entry.get(f)]
        if missing:
            raise RuntimeError(f"{path.name}: code {code} is missing {', '.join(missing)}")
        if entry["system"] not in VALID_SYSTEMS:
            raise RuntimeError(f"{path.name}: code {code} has unknown system '{entry['system']}' "
                               f"(use one of: {', '.join(sorted(VALID_SYSTEMS))})")
        if key in codes:
            raise RuntimeError(f"{path.name}: code {key} is listed twice")
        codes[key] = (entry["system"], entry["description"], entry["plain_english"])
    return codes


def _load_all(*paths: Path) -> dict[str, tuple[str, str, str]]:
    merged: dict[str, tuple[str, str, str]] = {}
    for path in paths:
        for code, entry in _load(path).items():
            if code in merged:
                raise RuntimeError(f"Code {code} is listed in more than one code file ({path.name})")
            merged[code] = entry
    return merged


# code -> (system, description, plain_english)
FALLBACK_CODES: dict[str, tuple[str, str, str]] = _load_all(MEDICAL_CODES_FILE, CPT_CODES_FILE, REVENUE_CODES_FILE)