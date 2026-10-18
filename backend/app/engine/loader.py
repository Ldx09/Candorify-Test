"""Loads bills from the synthetic-bills CSV format:

bill_id,line_no,description,code,quantity,unit_price,line_total
BILL-001,1,"Surgical dressing, sterile",A6402,1,22.00,22.00
BILL-001,,STATED SUBTOTAL,,,,2177.00
"""
import csv
from decimal import Decimal
from pathlib import Path

from app.engine.models import Bill, LineItem


def load_bills(csv_path: str | Path) -> list[Bill]:
    lines_by_bill: dict[str, list[LineItem]] = {}
    subtotal_by_bill: dict[str, Decimal] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            bill_id = row["bill_id"].strip()
            lines_by_bill.setdefault(bill_id, [])
            if row["description"].strip().upper() == "STATED SUBTOTAL":
                subtotal_by_bill[bill_id] = Decimal(row["line_total"])
                continue
            lines_by_bill[bill_id].append(LineItem(
                line_no=int(row["line_no"]),
                code=row["code"].strip(),
                description=row["description"].strip(),
                quantity=Decimal(row["quantity"]),
                unit_price=Decimal(row["unit_price"]),
                line_total=Decimal(row["line_total"]),
            ))

    missing = [b for b in lines_by_bill if b not in subtotal_by_bill]
    if missing:
        raise ValueError(f"No STATED SUBTOTAL row for: {', '.join(missing)}")

    return [Bill(bill_id=b, lines=lines, stated_subtotal=subtotal_by_bill[b])
            for b, lines in lines_by_bill.items()]