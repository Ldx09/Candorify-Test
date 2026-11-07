"""Reads real-world hospital and doctor bills (not our synthetic layout) into a Bill.

Used ONLY when the synthetic-bill reader (loader.load_bills_pdf) can't read a PDF, so our test and demo
bills keep going through exactly the same path as before.

How it reads a bill:
  1. Find the charges table: a header row with a "Description" column and an amount column
     ("Charges", "Amount", "Billed" ...). Words are placed into columns by their position on the page,
     so wrapped descriptions and side columns (Provider, Credits, Balance) are handled.
  2. Each row with an amount in the charges column is one charge. A row right under it with no amount
     continues its description. Payments, adjustments and insurance rows are skipped.
  3. "Total ... charges" sets the bill's stated total. With no total line, the charges are just added up.
  4. If there is no such table, a simpler fallback reads lines that end in a dollar amount.

Only charges are kept: names, addresses, account and insurance numbers are never read into the Bill.
Real summary bills rarely list per-item prices, so quantity = 1 and unit price = the amount (line math
can't be wrong by construction; the total and duplicate checks still work).
"""
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

import pdfplumber

from app.models.bill import Bill
from app.models.line_item import LineItem

_MONEY = re.compile(r"^\(?-?\$?-?[\d,]*\d\.\d{2}\)?$")       # 420.00, $933.08, -$5,741.45, (12.00)
_DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
_CODE = re.compile(r"^(\d{4}[0-9A-Z]|[A-CEGHJ-MP-TV]\d{4}|\d{4})$")  # CPT, HCPCS or revenue code
_LETTERS = re.compile(r"[A-Za-z]{3,}")

DESC_HEADERS = {"description", "service", "services", "item", "items"}
CHARGE_HEADERS = {"charges", "charge", "amount", "billed", "total"}
OTHER_AMOUNT_HEADERS = {"credits", "credit", "payments", "payment", "adjustments", "adjustment", "balance",
                        "paid", "insurance", "patient", "due", "allowed", "discount"}
CODE_HEADERS = {"code", "cpt", "hcpcs", "cpt/hcpcs", "rev", "revenue", "procedure"}
TEXT_HEADERS = {"provider", "physician", "doctor", "date", "dos", "qty", "quantity", "units", "rate", "price",
                "dept", "department", "modifier", "mod"}
AMOUNT_HEADERS = CHARGE_HEADERS | OTHER_AMOUNT_HEADERS
KNOWN_HEADERS = AMOUNT_HEADERS | CODE_HEADERS | TEXT_HEADERS

# Rows (or lines) about money already paid or owed, not charges.
SKIP_WORDS = re.compile(
    r"\b(payment|payments|paid|adjustment|adjustments|adjusted|insurance|credit|credits|refund|discount|"
    r"balance|due|deductible|coinsurance|co-?pay|copayment|responsibility|write[- ]?off|contractual|"
    r"plan|month|statement|guarantor|pay now|pay as)\b", re.IGNORECASE)
TOTAL_WORDS = re.compile(r"\btotal\b", re.IGNORECASE)
TOTAL_CHARGES = re.compile(r"\btotal\b.*\bcharges?\b|\bcharges?\b.*\btotal\b", re.IGNORECASE)

ROW_TOLERANCE = 3        # points: words this close vertically are on the same row
CONTINUATION_GAP = 16    # points: a row this close under a charge may continue its description


@dataclass
class _Col:
    name: str
    x0: float
    x1: float


@dataclass
class _Charge:
    description: list[str] = field(default_factory=list)
    amount: Decimal | None = None
    code: str = ""
    service_date: date | None = None
    bottom: float = 0.0
    page: int = 0


def _money(text: str) -> Decimal | None:
    t = text.strip()
    negative = t.startswith("-") or t.startswith("(") or "-$" in t
    t = t.strip("()").replace("$", "").replace(",", "").replace("-", "")
    try:
        value = Decimal(t)
    except InvalidOperation:
        return None
    return -value if negative else value


def _parse_date(text: str) -> date | None:
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", text)
    if not m:
        return None
    month, day, year = int(m[1]), int(m[2]), int(m[3])
    year = year + 2000 if year < 100 else year
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _rows(page) -> list[list[dict]]:
    """Words grouped into visual rows, top to bottom, left to right."""
    rows: list[list[dict]] = []
    for w in sorted(page.extract_words(keep_blank_chars=False), key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1][0]["top"] - w["top"]) <= ROW_TOLERANCE:
            rows[-1].append(w)
        else:
            rows.append([w])
    for r in rows:
        r.sort(key=lambda w: w["x0"])
    return rows


def _text(row: list[dict]) -> str:
    return " ".join(w["text"] for w in row)


def _find_header(row: list[dict]) -> tuple[list[_Col], int, int] | None:
    """If this row is a charges-table header, returns (columns, description column, charges column)."""
    cols = []
    for w in row:
        name = w["text"].strip().lower().strip(":")
        cols.append(_Col(name, w["x0"], w["x1"]))
    desc = next((i for i, c in enumerate(cols) if c.name in DESC_HEADERS), None)
    if desc is None:
        return None
    charge = next((i for i, c in enumerate(cols) if i > desc and c.name in CHARGE_HEADERS), None)
    if charge is None:
        return None
    return cols, desc, charge


def _amount_column(word: dict, cols: list[_Col], amount_cols: list[int]) -> int | None:
    """Picks the amount column whose header is horizontally closest to this number."""
    center = (word["x0"] + word["x1"]) / 2
    best, best_dist = None, None
    for i in amount_cols:
        dist = abs(center - (cols[i].x0 + cols[i].x1) / 2)
        if best_dist is None or dist < best_dist:
            best, best_dist = i, dist
    return best if best_dist is not None and best_dist <= 90 else None


def _desc_bounds(cols: list[_Col], desc_i: int, page_width: float) -> tuple[float, float]:
    """Left and right edges of the description column. Header words that are part of the description's
    own label (e.g. "Description / Service Classification") are not treated as separate columns."""
    before = [c for c in cols[:desc_i] if c.name in KNOWN_HEADERS]
    left = before[-1].x1 + 2 if before else 0
    after = [c for c in cols[desc_i + 1:] if c.name in KNOWN_HEADERS]
    if not after:
        return left, page_width
    nxt = after[0]
    if nxt.name in AMOUNT_HEADERS:          # numbers: descriptions can run right up to them
        return left, nxt.x0 - 4
    return left, (cols[desc_i].x1 + nxt.x0) / 2   # a text column (e.g. Provider): split the gap


def _read_tables(pdf) -> tuple[list[_Charge], Decimal | None]:
    charges: list[_Charge] = []
    total: Decimal | None = None
    for page_no, page in enumerate(pdf.pages):
        header = None
        last: _Charge | None = None       # the charge a continuation row can extend
        last_bottom = 0.0
        skipping = False                  # inside a payment/adjustment row's wrapped lines
        for row in _rows(page):
            text = _text(row)
            found = _find_header(row)
            if found:
                header, last, skipping = found, None, False
                continue
            if header is None:
                continue
            cols, desc_i, charge_i = header
            amount_cols = [i for i, c in enumerate(cols) if i > desc_i and c.name in AMOUNT_HEADERS]
            desc_left, desc_right = _desc_bounds(cols, desc_i, page.width)
            code_i = next((i for i, c in enumerate(cols) if c.name in CODE_HEADERS), None)

            if TOTAL_WORDS.search(text):
                if TOTAL_CHARGES.search(text):
                    amounts = [_money(w["text"]) for w in row if _MONEY.match(w["text"])]
                    amounts = [a for a in amounts if a is not None and a > 0]
                    if amounts:
                        total = amounts[-1]
                header, last = None, None         # the table ends at its total
                continue

            charge_amount = None
            other_amount = False
            for w in row:
                if _MONEY.match(w["text"]):
                    col = _amount_column(w, cols, amount_cols)
                    if col == charge_i:
                        charge_amount = _money(w["text"])
                    elif col is not None:
                        other_amount = True
            desc_words = [w["text"] for w in row if desc_left <= w["x0"] < desc_right
                          and not _MONEY.match(w["text"]) and not _DATE.match(w["text"])]
            row_top = min(w["top"] for w in row)

            if charge_amount is None:
                if other_amount or (desc_words and SKIP_WORDS.search(" ".join(desc_words))):
                    skipping, last = True, None   # a payment/adjustment row
                    last_bottom = max(w["bottom"] for w in row)
                    continue
                close = row_top - last_bottom <= CONTINUATION_GAP
                if desc_words and close and (last is not None or skipping):
                    if last is not None:
                        last.description.extend(desc_words)
                    last_bottom = max(w["bottom"] for w in row)
                    continue
                last, skipping = None, False
                continue

            desc_text = " ".join(desc_words)
            if charge_amount <= 0 or SKIP_WORDS.search(desc_text) or not _LETTERS.search(desc_text):
                skipping, last = True, None
                last_bottom = max(w["bottom"] for w in row)
                continue
            item = _Charge(description=list(desc_words), amount=charge_amount, page=page_no)
            first = row[0]["text"]
            if _DATE.match(first):
                item.service_date = _parse_date(first)
            if code_i is not None:
                for w in row:
                    if abs(w["x0"] - cols[code_i].x0) < 25 and _CODE.match(w["text"].upper()):
                        item.code = w["text"].upper()
            charges.append(item)
            last, skipping = item, False
            last_bottom = max(w["bottom"] for w in row)
    return charges, total


_LINE_END_MONEY = re.compile(r"^(?P<desc>.*?[A-Za-z].*?)\s+(?P<amt>\$?[\d,]*\d\.\d{2})$")


def _read_lines(pdf) -> tuple[list[_Charge], Decimal | None]:
    """Fallback for bills without a recognizable table: lines like 'Emergency Room ... $5,249.00'."""
    charges: list[_Charge] = []
    total = None
    for page_no, page in enumerate(pdf.pages):
        for raw in (page.extract_text() or "").splitlines():
            line = raw.strip()
            m = _LINE_END_MONEY.match(line)
            if not m:
                continue
            desc, amount = m["desc"].strip(" :-"), _money(m["amt"])
            if amount is None or amount <= 0:
                continue
            if TOTAL_WORDS.search(desc):
                if TOTAL_CHARGES.search(desc):
                    total = amount
                continue
            if SKIP_WORDS.search(desc) or not _LETTERS.search(desc) or ":" in desc:
                continue
            charges.append(_Charge(description=[desc], amount=amount, page=page_no))
    return charges, total


def _clean(words: list[str]) -> str:
    text = " ".join(words).strip(" ,;-")
    return re.sub(r"\s+", " ", text)[:500]


@dataclass
class RealBill:
    bill: Bill
    has_total: bool        # the bill printed a total we could compare against
    from_table: bool       # read from a charges table (vs. the line-by-line fallback)


def read_real_bill(path) -> RealBill | None:
    """Returns the bill's charges, or None if no charges could be found."""
    from app.engine.code_matching import match_code  # local import: keeps this module light to import

    with pdfplumber.open(path) as pdf:
        charges, total = _read_tables(pdf)
        from_table = bool(charges)
        if not charges:
            charges, total = _read_lines(pdf)
    if not charges:
        return None
    lines = []
    for n, ch in enumerate(charges, start=1):
        description = _clean(ch.description) or "Charge"
        # Quantity 1 and unit price = amount: summary bills don't print per-item prices, and guessing them
        # could create false line-math flags.
        lines.append(LineItem(line_no=n, code=ch.code or match_code(description), description=description,
                              quantity=Decimal(1), unit_price=ch.amount, line_total=ch.amount))
    summed = sum((ln.line_total for ln in lines), Decimal("0"))
    service_date = next((c.service_date for c in charges if c.service_date), None)
    bill = Bill(bill_id="UPLOAD", lines=lines, stated_subtotal=total if total is not None else summed,
                date_of_service=service_date)
    return RealBill(bill=bill, has_total=total is not None, from_table=from_table)