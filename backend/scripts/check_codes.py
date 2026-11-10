"""Checks every HCPCS and ICD-10-CM code in data/medical_codes.json against the live NLM database
(the same free government source the app uses), so the backup list stays correct.

    python -m scripts.check_codes

OK        = the code exists in NLM
MISSING   = NLM doesn't have this code (typo, retired code, or wrong system) -> fix or remove it
CPT and revenue codes aren't in NLM (CPT is licensed by the AMA), so they are skipped.
Our "description" may be worded a little differently from NLM's; NLM's official text is printed
next to ours so you can compare. The app always shows NLM's official text when NLM is reachable.
"""
import json
import sys
from pathlib import Path

import httpx

from app.translation import nlm_client as nlm

CODES_FILE = Path(__file__).resolve().parents[1] / "data" / "medical_codes.json"


def main() -> int:
    codes = json.loads(CODES_FILE.read_text(encoding="utf-8"))
    checked = missing = 0
    with httpx.Client(timeout=15) as client:
        for code, entry in codes.items():
            system = entry["system"]
            if system not in nlm.TABLES:
                continue
            checked += 1
            try:
                rows = nlm.search(system, code, client=client)
            except nlm.ProviderUnavailable as exc:
                print(f"Can't reach NLM ({exc}). Check your internet connection and try again.")
                return 2
            match = next((r for r in rows if r["code"].upper() == code.upper()), None)
            if match:
                official = match.get("long_desc") or match.get("name") or match.get("short_desc")
                print(f"OK       {system:10} {code:9} ours: {entry['description']}")
                if official.strip().lower() != entry["description"].strip().lower():
                    print(f"{'':30}NLM:  {official}")
            else:
                missing += 1
                print(f"MISSING  {system:10} {code:9} ours: {entry['description']}")
    print(f"\nChecked {checked} HCPCS/ICD-10-CM codes: {checked - missing} found, {missing} missing.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())