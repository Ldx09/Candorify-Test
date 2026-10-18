"""Generates synthetic medical bills with known, planted errors, plus an answer key.

Output uses the same CSV formats as data/synthetic_bills.csv and data/answer_key.csv.
Fully deterministic: the same --seed always produces the same bills. No AI is used,
so every planted error and every answer-key row is exact.

Run from the backend folder:
    python -m scripts.generate_bills --count 100 --seed 7
    python -m scripts.generate_bills --count 500 --seed 1 --vary-wording \
        --bills data/generated_bills.csv --key data/generated_answer_key.csv
"""
import argparse
import csv
import random
from decimal import Decimal
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
CENT = Decimal("0.01")

# Billing codes, descriptions and unit prices (same catalog as the provided sample bills).
# The second description is an alternative wording, used with --vary-wording to prove that
# duplicates are detected by code, not by text.
CATALOG = [
    ("99284", "Emergency department visit, level 4", "ER visit - level 4", Decimal("1450.00")),
    ("74177", "CT scan, abdomen and pelvis, with contrast", "CT abd/pelvis w/ contrast", Decimal("2380.00")),
    ("71046", "Chest X-ray, two views", "X-ray chest 2 views", Decimal("265.00")),
    ("80053", "Comprehensive metabolic panel", "CMP lab panel", Decimal("118.00")),
    ("85025", "Complete blood count with differential", "CBC w/ diff", Decimal("96.00")),
    ("96365", "IV infusion, initial hour", "IV infusion 1st hr", Decimal("412.00")),
    ("J2405", "Ondansetron injection, 4 mg", "Zofran inj 4mg", Decimal("54.00")),
    ("J7030", "Sodium chloride 0.9% IV solution, 1000 mL", "Normal saline 1000cc", Decimal("78.00")),
    ("A6402", "Surgical dressing, sterile", "Sterile gauze dressing", Decimal("22.00")),
    ("94760", "Pulse oximetry, single determination", "Pulse ox check", Decimal("38.00")),
    ("0250", "Pharmacy, general supplies", "Pharmacy supplies", Decimal("65.00")),
    ("0710", "Recovery room, per 30 minutes", "Recovery rm 30 min", Decimal("340.00")),
    # Codes that trigger the follow-up questions (room / ICU nights, ambulance, blood draws):
    ("0120", "Room and board, semi-private", "Semi-private room", Decimal("2800.00")),
    ("0200", "Intensive care, general", "ICU general", Decimal("6500.00")),
    ("A0427", "Ambulance service, ALS, emergency transport, level 1", "ALS ambulance emergency", Decimal("1250.00")),
    ("A0425", "Ground ambulance mileage, per mile", "Ambulance miles", Decimal("28.00")),
    ("36415", "Routine venipuncture (blood draw)", "Blood draw", Decimal("18.00")),
]

DEFECT_TYPES = ["none", "duplicate", "line_math", "subtotal", "mixed"]


def _clean_lines(rng: random.Random) -> list[dict]:
    """4-8 correct lines. Codes are all different, so a clean bill can never contain a duplicate."""
    picks = rng.sample(CATALOG, rng.randint(4, 8))
    lines = []
    for code, desc, _alt, price in picks:
        qty = rng.randint(1, 3)
        lines.append({"code": code, "description": desc, "quantity": qty,
                      "unit_price": price, "line_total": (price * qty).quantize(CENT)})
    return lines


def _plant_duplicate(rng: random.Random, lines: list[dict], vary_wording: bool) -> str:
    """Copies one line and inserts the copy later on the bill. Returns the answer-key text."""
    src_index = rng.randrange(len(lines))
    original = lines[src_index]
    copy = dict(original)
    if vary_wording and rng.random() < 0.5:
        copy["description"] = next(alt for c, _d, alt, _p in CATALOG if c == original["code"])
    insert_at = rng.randint(src_index + 1, len(lines))  # always after the original
    lines.insert(insert_at, copy)
    return f"Duplicate line: {original['description']} ({original['code']})"


def _plant_line_math(rng: random.Random, lines: list[dict], avoid_code: str | None = None) -> str:
    """Makes one line total wrong by a whole-dollar amount. Returns the answer-key text."""
    candidates = [i for i, ln in enumerate(lines) if ln["code"] != avoid_code]
    i = rng.choice(candidates)
    correct = lines[i]["line_total"]
    while True:
        wrong = correct + Decimal(rng.choice([-1, 1]) * rng.randint(5, 200))
        if wrong > 0:
            break
    lines[i]["line_total"] = wrong.quantize(CENT)
    return f"Line total != unit price x quantity on line {i + 1} ({lines[i]['code']})"


def generate_bill(rng: random.Random, bill_id: str, defect: str, vary_wording: bool):
    lines = _clean_lines(rng)
    planted = "none"
    subtotal_offset = Decimal("0")

    if defect == "duplicate":
        planted = _plant_duplicate(rng, lines, vary_wording)
    elif defect == "line_math":
        planted = _plant_line_math(rng, lines)
    elif defect == "subtotal":
        subtotal_offset = Decimal(rng.randint(1000, 60000)) / 100 * rng.choice([-1, 1])  # $10.00-$600.00
        planted = "Stated subtotal does not equal sum of line totals"
    elif defect == "mixed":
        dup_text = _plant_duplicate(rng, lines, vary_wording)
        dup_code = dup_text.rsplit("(", 1)[1].rstrip(")")
        _plant_line_math(rng, lines, avoid_code=dup_code)  # math error on a different item
        planted = "Duplicate line AND line-total arithmetic error"

    sum_of_lines = sum((ln["line_total"] for ln in lines), Decimal("0")).quantize(CENT)
    stated_subtotal = (sum_of_lines + subtotal_offset).quantize(CENT)
    if defect == "subtotal" and stated_subtotal <= 0:  # keep subtotals realistic
        stated_subtotal = (sum_of_lines + abs(subtotal_offset)).quantize(CENT)

    for n, ln in enumerate(lines, start=1):
        ln["line_no"] = n

    key_row = {"bill_id": bill_id, "defect_type": defect, "planted_error": planted,
               "true_sum_of_lines": f"{sum_of_lines:.2f}", "stated_subtotal": f"{stated_subtotal:.2f}"}
    return lines, stated_subtotal, key_row


def main() -> None:
    p = argparse.ArgumentParser(description="Generate synthetic bills with planted errors + answer key.")
    p.add_argument("--count", type=int, default=100, help="number of bills (default 100)")
    p.add_argument("--seed", type=int, default=42, help="same seed = same bills (default 42)")
    p.add_argument("--prefix", default="GEN", help="bill id prefix (default GEN -> GEN-0001)")
    p.add_argument("--vary-wording", action="store_true",
                   help="half of the duplicates use different wording for the same code")
    p.add_argument("--bills", type=Path, default=DATA / "generated_bills.csv")
    p.add_argument("--key", type=Path, default=DATA / "generated_answer_key.csv")
    args = p.parse_args()

    if args.count < 1:
        p.error("--count must be at least 1")

    rng = random.Random(args.seed)
    # Even mix of defect types (each appears count/5 times, +-1), in random order.
    defects = [DEFECT_TYPES[i % len(DEFECT_TYPES)] for i in range(args.count)]
    rng.shuffle(defects)

    args.bills.parent.mkdir(parents=True, exist_ok=True)
    args.key.parent.mkdir(parents=True, exist_ok=True)
    width = max(3, len(str(args.count)))

    with open(args.bills, "w", newline="", encoding="utf-8") as bf, \
         open(args.key, "w", newline="", encoding="utf-8") as kf:
        bills_w = csv.writer(bf)
        bills_w.writerow(["bill_id", "line_no", "description", "code", "quantity", "unit_price", "line_total"])
        key_w = csv.DictWriter(kf, fieldnames=["bill_id", "defect_type", "planted_error",
                                               "true_sum_of_lines", "stated_subtotal"])
        key_w.writeheader()

        for n, defect in enumerate(defects, start=1):
            bill_id = f"{args.prefix}-{n:0{width}d}"
            lines, stated_subtotal, key_row = generate_bill(rng, bill_id, defect, args.vary_wording)
            for ln in lines:
                bills_w.writerow([bill_id, ln["line_no"], ln["description"], ln["code"], ln["quantity"],
                                  f"{ln['unit_price']:.2f}", f"{ln['line_total']:.2f}"])
            bills_w.writerow([bill_id, "", "STATED SUBTOTAL", "", "", "", f"{stated_subtotal:.2f}"])
            key_w.writerow(key_row)

    counts = {d: defects.count(d) for d in DEFECT_TYPES}
    print(f"Wrote {args.count} bills -> {args.bills}")
    print(f"Wrote answer key      -> {args.key}")
    print("Defect mix: " + ", ".join(f"{d}={c}" for d, c in counts.items()))


if __name__ == "__main__":
    main()