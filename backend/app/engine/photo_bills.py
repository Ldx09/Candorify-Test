"""Reads a bill from PHOTOS. The photos are read on the user's phone (Tesseract.js, see frontend/photo.js);
only the text lines are sent here, never the image.

Phone text recognition makes small mistakes ("S87.00" for "$87.00", "87 .00", odd dashes), so each line is
cleaned first. Then the same rules as the real-bill line reader apply (real_bills.py): a line ending in an
amount is a charge, payments/adjustments are skipped, "Total charges" / "Billed to insurance" is the total,
department subtotal lines are dropped when their items add up, and codes printed in the text are kept.
Like real bills, only charges are kept (no names, addresses or account numbers).
"""
import re
from decimal import Decimal

from app.engine import real_bills as rb
from app.models.bill import Bill
from app.models.line_item import LineItem

MAX_PAGES = 5
_AMOUNT = r"\(?-?\$?-?[\d,]*\d\.\d{2}\)?"
_TRAILING_AMOUNTS = re.compile(rf"^(?P<desc>.*?)\s*(?P<amts>(?:{_AMOUNT}\s*)+)$")
_LEADING_DATE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4})\s+")


def clean_line(line: str) -> str:
    """Fixes the usual phone-OCR slips in amounts and dashes."""
    t = line.replace("\u2014", "-").replace("\u2013", "-").replace("\u2212", "-")
    t = re.sub(r"(?<![A-Za-z])[S\u00a7](?=\d[\d,]*\.\d{2}\b)", "$", t)   # S87.00 -> $87.00
    t = re.sub(r"\$\s+(?=\d)", "$", t)                                    # $ 87.00 -> $87.00
    t = re.sub(r"(\d)\s*([.,])\s*(\d{2})\b(?![\d,])", r"\1.\3", t)       # 87 .00 / 87,00 -> 87.00
    t = re.sub(r"(\d),(\d{3}\.\d{2})", r"\1,\2", t)
    t = re.sub(r"^[^\w$(\-]+", "", t.strip())                             # stray "|" or "•" at the start
    return re.sub(r"\s+", " ", t).strip()


def _amount_columns(line: str) -> tuple[int, int] | None:
    """For a header row like 'Date Description Provider Charges Credits Balance': (number of amount
    columns, position of the charges column among them). None if it isn't such a header."""
    words = [w.strip(":").lower() for w in line.split()]
    if not any(w in rb.DESC_HEADERS for w in words):
        return None
    amounts = [w for w in words if w in rb.AMOUNT_HEADERS]
    charge = next((i for i, w in enumerate(amounts) if w in rb.CHARGE_HEADERS), None)
    if len(amounts) < 2 or charge is None:
        return None
    return len(amounts), charge


def _charges_from_lines(pages: list[list[str]]) -> tuple[list[rb._Charge], Decimal | None]:
    charges: list[rb._Charge] = []
    total = None
    last: rb._Charge | None = None
    extra = 0
    columns = None
    for page_no, page in enumerate(pages):
        for raw in page:
            line = clean_line(raw)
            if not line:
                continue
            header = _amount_columns(line)
            if header:
                columns, last = header, None
                continue
            m = _TRAILING_AMOUNTS.match(line)
            if not m or not rb._LETTERS.search(m["desc"]):
                if (m is None and last is not None and extra < rb.MAX_CONTINUATION and rb._LETTERS.search(line)
                        and not (rb.SKIP_WORDS.search(line) or rb.TOTAL_WORDS.search(line) or "$" in line)):
                    last.description.append(line)
                    extra += 1
                    continue
                if m is None:
                    last = None
                continue
            amounts = [rb._money(a) for a in re.findall(_AMOUNT, m["amts"])]
            if len(amounts) > 1 and columns and len(amounts) == columns[0]:
                amount = amounts[columns[1]]                 # the Charges column of a multi-amount row
            elif len(amounts) > 1 and columns:
                amount = amounts[0]                         # some columns empty: Charges comes first
            else:
                amount = amounts[-1]
            desc = m["desc"].strip(" :-")
            last = None
            if amount is None or amount <= 0:
                continue
            if rb.BILLED_TOTAL.search(desc):
                total = amount
                continue
            if rb.TOTAL_WORDS.search(desc):
                if rb.TOTAL_CHARGES.search(desc):
                    total = amount
                continue
            if rb.SKIP_WORDS.search(desc) or ":" in rb._QTY_IN_TEXT.sub("", desc):
                continue
            item = rb._Charge(amount=amount, page=page_no)
            date = _LEADING_DATE.match(desc)
            if date:
                item.service_date = rb._parse_date(date[1])
                desc = desc[date.end():]
            item.description = [desc]
            charges.append(item)
            last, extra = item, 0
    charges = rb._drop_group_totals(charges)
    for ch in charges:
        text = " ".join(ch.description)
        found = rb._CODE_IN_TEXT.search(text)
        if found:
            ch.code = found[1].upper()
            ch.description = [rb._CODE_IN_TEXT.sub("", text)]
    return charges, total


def _facility(pages: list[list[str]]) -> str | None:
    for page in pages:
        for line in page:
            for pattern in rb._FACILITY:
                m = pattern.match(clean_line(line))
                if m and rb._LETTERS.search(m["name"]) and not re.search(r"\d{3}", m["name"]):
                    return m["name"].strip(" ,;-")[:100]
    return None


def read_photo_text(pages: list[list[str]]) -> rb.RealBill | None:
    """The bill's charges from the text of up to MAX_PAGES photos, or None if no charges were found."""
    from app.engine.code_matching import match_code

    charges, total = _charges_from_lines(pages[:MAX_PAGES])
    if not charges:
        return None
    lines = []
    for n, ch in enumerate(charges, start=1):
        description = rb._clean(ch.description) or "Charge"
        lines.append(LineItem(line_no=n, code=ch.code or match_code(description), description=description,
                              quantity=Decimal(1), unit_price=ch.amount, line_total=ch.amount))
    summed = sum((ln.line_total for ln in lines), Decimal("0"))
    service_date = next((c.service_date for c in charges if c.service_date), None)
    bill = Bill(bill_id="PHOTO", lines=lines, stated_subtotal=total if total is not None else summed,
                date_of_service=service_date)
    from app.engine.payments import extract_payments   # local import: payments.py imports this module
    bill.payments = extract_payments(pages[:MAX_PAGES], bill.stated_subtotal)
    return rb.RealBill(bill=bill, has_total=total is not None, from_table=False, provider_name=_facility(pages))