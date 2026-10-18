"""Runs the check engine on every synthetic bill and compares the flags with the answer key.

Run from the backend folder:
    python -m scripts.evaluate_engine                       (the 20 provided bills)
    python -m scripts.evaluate_engine --bills data/generated_bills.csv --key data/generated_answer_key.csv
"""
import argparse
import csv
import re
import sys
from pathlib import Path

from app.engine.checks import run_checks
from app.engine.loader import load_bills

DATA = Path(__file__).resolve().parent.parent / "data"

# Which rules the engine should fire for each defect type in the answer key.
EXPECTED_RULES = {
    "none": set(),
    "duplicate": {"duplicate_line"},
    "line_math": {"line_math"},
    "subtotal": {"subtotal_mismatch"},
    "mixed": {"duplicate_line", "line_math"},
}


def main() -> int:
    p = argparse.ArgumentParser(description="Check the engine against an answer key.")
    p.add_argument("--bills", type=Path, default=DATA / "synthetic_bills.csv")
    p.add_argument("--key", type=Path, default=DATA / "answer_key.csv")
    p.add_argument("--quiet", action="store_true", help="only print failures and the final score")
    args = p.parse_args()

    bills = {b.bill_id: b for b in load_bills(args.bills)}
    with open(args.key, newline="", encoding="utf-8") as f:
        key = list(csv.DictReader(f))

    passed = 0
    if not args.quiet:
        print(f"{'Bill':<10}{'Expected':<34}{'Engine found':<34}Result")
        print("-" * 84)
    for row in key:
        report = run_checks(bills[row["bill_id"]])
        found = {fl.rule for fl in report.flags}
        expected = EXPECTED_RULES[row["defect_type"]]
        ok = found == expected

        # Where the answer key names a line or code, check the engine pointed at the same one.
        planted = row["planted_error"]
        m = re.search(r"on line (\d+) \((\w+)\)", planted)
        if ok and m:
            ok = any(fl.rule == "line_math" and fl.line_no == int(m[1]) and fl.code == m[2] for fl in report.flags)
        m = re.search(r"Duplicate line: .*\((\w+)\)$", planted)
        if ok and m:
            ok = any(fl.rule == "duplicate_line" and fl.code == m[1] for fl in report.flags)

        passed += ok
        if not args.quiet or not ok:
            print(f"{row['bill_id']:<10}{', '.join(sorted(expected)) or 'no flags':<34}"
                  f"{', '.join(sorted(found)) or 'no flags':<34}{'PASS' if ok else 'FAIL'}")

    if not args.quiet:
        print("-" * 84)
    print(f"{passed}/{len(key)} bills correct")
    return 0 if passed == len(key) else 1


if __name__ == "__main__":
    sys.exit(main())