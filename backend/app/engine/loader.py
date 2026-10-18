"""Reads synthetic bills from CSV or PDF into Bill / LineItem objects.

    load_bills("data/synthetic_bills.csv")   # or .pdf, picked by file extension

CSV format:
    bill_id,line_no,description,code,quantity,unit_price,line_total
    BILL-001,1,"Surgical dressing, sterile",A6402,1,22.00,22.00
    BILL-001,,STATED SUBTOTAL,,,,2177.00

PDF format (one itemized statement per bill):
    Account #: BILL-001 ...
    Code Description Qty Unit price Line total
    A6402 Surgical dressing, sterile 1 $22.00 $22.00
    Total charges $2,177.00
"""
import csv
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pdfplumber

from app.models.bill import Bill
from app.models.line_item import LineItem


def load_bills(path: str | Path) -> list[Bill]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_bills_csv(path)
    if suffix == ".pdf":
        return load_bills_pdf(path)
    raise ValueError(f"Unsupported bill file type '{suffix}'. Use .csv or .pdf")


def parse_date(text: str | None) -> date | None:
    """Accepts 09/01/2026 (as printed on bills) or 2026-09-01. Returns None if blank or unreadable."""
    text = (text or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


# ---------- CSV ----------

def load_bills_csv(path: str | Path) -> list[Bill]:
    lines_by_bill: dict[str, list[LineItem]] = {}
    subtotal_by_bill: dict[str, Decimal] = {}
    date_by_bill: dict[str, date | None] = {}

    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            bill_id = row["bill_id"].strip()
            lines_by_bill.setdefault(bill_id, [])
            if row.get("date_of_service"):  # optional column
                date_by_bill[bill_id] = parse_date(row["date_of_service"])
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

    return [Bill(bill_id=b, lines=lines, stated_subtotal=subtotal_by_bill[b], date_of_service=date_by_bill.get(b))
            for b, lines in lines_by_bill.items()]


# ---------- PDF ----------

_MONEY = r"\$?(-?[\d,]+\.\d{2})"
_ACCOUNT = re.compile(r"Account #:\s*(\S+)")
_HEADER = re.compile(r"^Code\s+Description\s+Qty\s+Unit price\s+Line total$", re.IGNORECASE)
_LINE = re.compile(rf"^(\S+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+{_MONEY}\s+{_MONEY}$")
_TOTAL = re.compile(rf"^Total charges\s+{_MONEY}$", re.IGNORECASE)
_DATE = re.compile(r"Date of service:\s*(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE)


def _money(text: str) -> Decimal:
    return Decimal(text.replace(",", ""))


def load_bills_pdf(path: str | Path) -> list[Bill]:
    """Each bill starts at an 'Account #:' line, lists charges under the column header,
    and ends at 'Total charges'. A bill may continue across pages with the same Account #.
    Any unreadable line inside the charges table stops loading with a clear error."""
    lines_by_bill: dict[str, list[LineItem]] = {}
    subtotal_by_bill: dict[str, Decimal] = {}
    date_by_bill: dict[str, date | None] = {}

    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            bill_id = None
            in_table = False
            for raw in text.splitlines():
                row = raw.strip()
                if m := _ACCOUNT.search(row):
                    bill_id = m[1]
                    lines_by_bill.setdefault(bill_id, [])
                    continue
                if (m := _DATE.search(row)) and bill_id and not in_table:
                    date_by_bill.setdefault(bill_id, parse_date(m[1]))
                if _HEADER.match(row):
                    if bill_id is None:
                        raise ValueError(f"Page {page_no}: charges table found before an 'Account #' line")
                    in_table = True
                    continue
                if not in_table:
                    continue
                if m := _TOTAL.match(row):
                    subtotal_by_bill[bill_id] = _money(m[1])
                    in_table = False
                    continue
                m = _LINE.match(row)
                if not m:
                    raise ValueError(f"Page {page_no} ({bill_id}): could not read charge line: {row!r}")
                lines = lines_by_bill[bill_id]
                lines.append(LineItem(
                    line_no=len(lines) + 1,
                    code=m[1],
                    description=m[2],
                    quantity=Decimal(m[3]),
                    unit_price=_money(m[4]),
                    line_total=_money(m[5]),
                ))

    if not lines_by_bill:
        raise ValueError("No bills found in PDF (no 'Account #' lines)")
    missing = [b for b in lines_by_bill if b not in subtotal_by_bill]
    if missing:
        raise ValueError(f"No 'Total charges' line for: {', '.join(missing)}")

    return [Bill(bill_id=b, lines=lines, stated_subtotal=subtotal_by_bill[b], date_of_service=date_by_bill.get(b))
            for b, lines in lines_by_bill.items()]