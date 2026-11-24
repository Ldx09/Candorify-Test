"""Checks the photo reader against bills whose correct answer we know, like evaluate_engine does for PDFs.

Each case is the text a phone read from a bill photo (what frontend/photo.js sends) plus the right answer:
the charges, the total, the flags, and optionally the payments. The cases in data/photo_cases.json use FAKE
bills only (the demo/synthetic bills and sample statements, photographed easy, hard and tilted).

To test a REAL bill photo without committing it: read the photo on the Upload page, then in the browser
console run  copy(JSON.stringify(CandorifyPhoto.lastPages))  and save a file in backend/photo_cases_local/
(that folder is in .gitignore) like:
    {"name": "my-er-bill", "pages": <paste here>,
     "expect": {"charges": ["120.00", "45.50"], "total": "165.50", "flags": []}}

Run from the backend folder:
    python -m scripts.evaluate_photos              (all cases)
    python -m scripts.evaluate_photos -v           (also show what was read for failures)
"""
import argparse
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

from app.engine.checks import run_checks
from app.engine.photo_bills import read_photo_text

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "data" / "photo_cases.json"
LOCAL = ROOT / "photo_cases_local"


def load_cases() -> list[dict]:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if LOCAL.is_dir():
        for f in sorted(LOCAL.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            for case in data if isinstance(data, list) else [data]:
                case.setdefault("name", f.stem)
                case["source"] = f"local: {f.name}"
                cases.append(case)
    return cases


def check(case: dict) -> list[str]:
    """What's wrong with the reader's answer for this case ([] = all correct)."""
    exp = case["expect"]
    r = read_photo_text(case["pages"])
    if r is None:
        return ["no charges found"]
    bill = r.bill
    problems = []
    got = Counter(f"{ln.line_total:.2f}" for ln in bill.lines)
    want = Counter(exp["charges"])
    if got != want:
        missing, extra = list((want - got).elements()), list((got - want).elements())
        problems.append(f"charges: missing {missing}, extra {extra}")
    if f"{bill.stated_subtotal:.2f}" != exp["total"]:
        problems.append(f"total: read {bill.stated_subtotal:.2f}, should be {exp['total']}")
    if "has_total" in exp and r.has_total != exp["has_total"]:
        problems.append(f"has_total: {r.has_total}, should be {exp['has_total']}")
    flags = sorted({f.rule for f in run_checks(bill).flags})
    if flags != sorted(exp["flags"]):
        problems.append(f"flags: {flags}, should be {sorted(exp['flags'])}")
    for key, value in exp.get("payments", {}).items():
        have = getattr(bill.payments, key, None) if bill.payments else None
        if have is None or Decimal(value) != have:
            problems.append(f"payments.{key}: {have}, should be {value}")
    return problems


def main() -> int:
    p = argparse.ArgumentParser(description="Check the photo reader against known answers.")
    p.add_argument("-v", "--verbose", action="store_true", help="show what was read for failures")
    args = p.parse_args()
    cases = load_cases()
    passed = 0
    for case in cases:
        problems = check(case)
        if problems:
            print(f"FAIL  {case['name']:<34} {case.get('source', '')}")
            for line in problems:
                print(f"        {line}")
            if args.verbose:
                r = read_photo_text(case["pages"])
                for ln in (r.bill.lines if r else []):
                    print(f"          {ln.code or '-':>6}  {ln.description[:50]:<50} {ln.line_total}")
        else:
            passed += 1
            print(f"PASS  {case['name']:<34} {case.get('source', '')}")
    print("-" * 84)
    print(f"{passed}/{len(cases)} photo bills read correctly")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())