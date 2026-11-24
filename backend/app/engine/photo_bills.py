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
_LEADING_DATE = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+")
_LEADING_TEXT_DATE = re.compile(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\s+",
                                re.IGNORECASE)   # "Dec 03, 2025 Office visit"
_MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                        "dec"), start=1)}
_STARTS_WITH_DATE = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
                               re.IGNORECASE)
# A clinician's name printed in a Provider column, e.g. "Emma R. Patel, MD" (not part of the service)
_CLINICIAN = re.compile(
    r"\s*\b(?:[DdPp]r[._]?\s*)?(?:[A-Z][a-z]+\s+)?(?:[A-Z][._]\s*)?[A-Z][A-Za-z'-]+,?\s+"
    r"(?:M\.?\s?D|D\.?\s?O|NP|PA-C|PA|DPM|DDS|DMD|CRNA|APRN|FNP)\b\.?")
_GARBLED_DATE = re.compile(r"^(?=(?:\S*\d){3})[0-9oOsSlI]{6,10}\s+")   # "o1s202s" = a misread 01/15/2025
# The code column: 99203 / J1100 / 0120, or a misread one ("AB402", "oeo72", "4 761"); photo_codes fixes it
_LEADING_CODE = re.compile(r"^((?=[A-Za-z0-9]*\d)[A-Za-z0-9]{4,5}|\d{1,2} \d{3,4})\s+(?=[A-Za-z(])")
_QTY_UNIT = re.compile(r"^(?P<desc>.*\S)\s+(?P<qty>\d{1,3})$")   # "... level 4  1" before Unit price / Line total
_NAME_BEFORE_CREDENTIAL = re.compile(r"\s+[A-Z][a-z]+\s+[A-Z][A-Za-z'-]+,\s*$")
_CREDENTIAL_END = re.compile(r"(?:^|\s+)(?:M\.?D|D\.?O|NP|PA-C|DPM|APRN|FNP)\.?\s*$")
_SUBTOTAL = re.compile(r"\bsub[- ]?totals?\b", re.IGNORECASE)   # a page or section subtotal, not a charge
_DATE_RANGE_END = re.compile(r"^-\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*")   # "- 04/25/2026" after the first date
_DATE_CELL_ANY = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(\s*-\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4})?|"
                            r"[A-Za-z]{3,9}\.? \d{1,2},? \d{4})$")
_CODE_CELL = re.compile(r"^(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{3,5}$|^[A-Z]{3}$")
_QTY_CELL = re.compile(r"^(\d{1,3})\s*(?:days?|units?|ea)?$", re.IGNORECASE)
_PROVIDER_NAME = re.compile(r",\s*(?:M\.?\s?D|D\.?\s?O|NP|PA-C|DPM|APRN|FNP)\b")
_TRAILING_QTY = re.compile(r"\s+\d{1,2}$")                     # the Qty column: "Throat culture 1"
_NEW_CHARGES = re.compile(r"^new charges\b", re.IGNORECASE)    # "New Charges: $892.00" in a summary box
_SERVICE_DATE = re.compile(r"\bdates?(?:\(s\))? of service\b[^0-9]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE)
_TOTAL_ROW = re.compile(r"\btotals?\b", re.IGNORECASE)          # "Total" and "Totals"
_TOTAL_CHARGES_ANYWHERE = re.compile(r"\b(?:total charges|billed to insurance)\b\s*:?\s*\$?([\d,]+\.\d{2})", re.IGNORECASE)


def _add_dot(m: re.Match) -> str:
    """'$21000' -> '$210.00': the phone dropped the dot. Only for $-amounts with no dot at all."""
    digits = m[0][1:].replace("O", "0").replace("o", "0")
    return f"${digits[:-2]}.{digits[-2:]}"


def clean_line(line: str) -> str:
    """Fixes the usual phone-OCR slips in amounts and dashes."""
    t = line.replace("—", "-").replace("–", "-").replace("−", "-")
    t = re.sub(r"\b(Amount|Balance|Total|Current|Patient|Insurance|Account|Previous|Prior)(?=[A-Z])", r"\1 ", t)
    # ^ "AmountDue" -> "Amount Due": the phone dropped the space
    t = re.sub(r"(?<![A-Za-z])[S§](?=\d[\d,]*\.\d{2}\b)", "$", t)        # S87.00 -> $87.00
    t = re.sub(r"\$\s+(?=\d)", "$", t)                                    # $ 87.00 -> $87.00
    t = re.sub(r"\$(\d{1,3})\.(\d{3})\s(\d{2})\b", r"$\1,\2.\3", t)           # $3.400 00 -> $3,400.00
    t = re.sub(r"\$(\d{1,3})\.(\d{3})\.(\d{2})\b", r"$\1,\2.\3", t)           # $1.236.00 -> $1,236.00
    t = re.sub(r"(\d)\s*([.,])\s*(\d{2})\b(?![\d,])", r"\1.\3", t)       # 87 .00 / 87,00 -> 87.00
    t = re.sub(r"(\d),(\d{3}\.\d{2})", r"\1,\2", t)
    t = re.sub(r"\$(\d{1,3})\s(\d{3}\.\d{2})\b", r"$\1,\2", t)               # $11 200.00 -> $11,200.00
    t = re.sub(r"(?<=\.\d\d\s)5(\d{1,3})\s(\d{3}\.\d{2})\b", r"$\1,\2", t)   # "51 450.00" ($ read as 5) -> $1,450.00
    t = re.sub(r"\$([\d,]*\d)\s(\d{2})\b(?![.,]?\d)", r"$\1.\2", t)           # $44 00 -> $44.00
    t = re.sub(r"(?<=\.\d)[¢c](?=\s|$)", "0", t)                             # $1,450.0¢ -> $1,450.00
    t = t.replace("¢", "$")                                               # ¢45.00 -> $45.00
    t = re.sub(r"\$(?=[\dOo,]*\d)[\dOo,]+\.[\dOo]{2}\b",                     # $1O5.00 -> $105.00
               lambda m: m[0].replace("O", "0").replace("o", "0"), t)
    t = re.sub(r"\$[\dOo]{3,7}(?=[^\d.,]|$)", _add_dot, t)                  # $21000 / $000 -> $210.00 / $0.00
    t = re.sub(r"(?<=\d)[}{\]\[]", "", t)                                  # "$112.00}" -> "$112.00"
    t = re.sub(r"(?:(?<=\s)|^)(?:[|=~}{\]\[]+|=~)(?=\s|$)", " ", t)          # stray | = ~ marks between words
    t = re.sub(r"(?<=\.\d\d)\s+-(?=\s+[-$(]?\d|\s*$)", " ", t)            # "265.00 - -132.50": a dash = empty cell
    t = re.sub(r"^[^\w$(\-]+", "", t.strip())                             # stray "|" or "•" at the start
    t = re.sub(r"(?<=\d)[\s|\]\[!_~`'\",;:]+$", "", t)                    # stray "|" or "]" after the last amount
    return re.sub(r"\s+", " ", t).strip()


_GAP = re.compile(r"\s{4,}|\s\|\s|^\||\|$")          # a wide gap or a "|" border between two columns
_AMOUNT_CELL = re.compile(rf"^(?:[-—–]?\s*{_AMOUNT}\s*)+$")       # a cell holding only amounts
_AMOUNT_WITH_SPECK = re.compile(rf"^((?:[-—–]?\s*{_AMOUNT}\s*)+?)\s+[^\s$]{{1,2}}$")   # "-$6.00 1"
_DATE_CELL = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")


def logical_lines(raw: str) -> list[str]:
    """Phones keep wide gaps between a bill's columns. A table row (amounts side by side at the end) or a
    header row stays one line; a two-column page ("Insurance Payments  -$255.00   a $30.00 copay. Please...")
    is split so each label keeps only its own amount. Returns cleaned lines."""
    if len(re.findall(r"\$\d", raw)) >= 3:                       # a table row: "~$168.00" is a misread "-$168.00"
        raw = re.sub(r"(?:(?<=\s)|^)~+\s*-?\s*(?=\$\d)", "-", raw)
    whole = clean_line(raw)
    cells = [c.strip() for c in _GAP.split(raw) if c and c.strip() and c.strip() not in "—–-|"]
    if len(cells) < 3 or _amount_columns(whole):
        return [whole] if whole else []
    cells = [clean_line(c) for c in cells]
    tidy, seen_amount = [], False
    for c in cells:                       # specks after the amounts (":", "1", "»") are not cells
        m = _AMOUNT_WITH_SPECK.match(c)
        if m:
            c = m[1]
        if (seen_amount and re.fullmatch(r"[^\w$]{1,3}|\w", c or "x")) or re.fullmatch(r"[A-Za-z]{1,2}|[^\w$]{1,3}", c or "x"):
            continue                      # "Xo", "LT", ":" between or after the amounts
        seen_amount = seen_amount or bool(_AMOUNT_CELL.match(c))
        if c:
            tidy.append(c)
    cells = tidy
    if len(cells) < 2:
        return [whole] if whole else []
    whole = clean_line(" ".join(cells))
    kinds = [bool(_AMOUNT_CELL.match(c)) for c in cells]
    first_amount = kinds.index(True) if True in kinds else len(kinds)
    one_amount_row = (kinds.count(True) == 1 and kinds[-1] and not cells[-2].endswith(":"))
    if True not in kinds:
        return [whole]          # plain text
    if all(kinds[first_amount:]) and (len(kinds) - first_amount >= 2 or one_amount_row):
        return ["\t".join(cells)]   # a table row: amounts only at the end; a tab marks each column
    out, label = [], []
    merged_cells, merged_kinds = [], []
    for cell, is_amount in zip(cells, kinds):      # "Patient Name:" + "Jordan Ellis" -> one cell
        if merged_cells and not is_amount and not merged_kinds[-1] and merged_cells[-1].endswith(":") \
                and not cell.endswith(":"):
            merged_cells[-1] += " " + cell
            continue
        merged_cells.append(cell)
        merged_kinds.append(is_amount)
    for cell, is_amount in zip(merged_cells, merged_kinds):
        if is_amount:
            keep = label[-1:]
            if len(label) >= 2 and _DATE_CELL.match(label[-2]):   # "01/28/2025", "Insurance Payment", "-$520.00"
                keep = label[-2:]
            out.append(" ".join(keep + [cell]))
            out.extend(label[:len(label) - len(keep)])
            label = []
        else:
            label.append(cell)
    out.extend(label)
    return [line for line in out if line]


_ONLY_AMOUNTS = re.compile(rf"^(?:{_AMOUNT}\s*){{2,}}$")
_CODE_ROW_NO_AMOUNT = re.compile(r"^(?:\d{5}|[A-V]\d{4}|0\d{3})\s+[A-Za-z]")


def _rejoin_rows(lines: list[str]) -> list[str]:
    """A tilted photo can put a row's amounts on their own line, just above or below its code and name:
    '$15.00 -$9.00 -$6.00' + '96372 Therapeutic injection, IM' -> one row."""
    out: list[str] = []
    used = set()
    for i, line in enumerate(lines):
        if i in used:
            continue
        if _ONLY_AMOUNTS.match(line):
            for j in (i - 1, i + 1):
                if 0 <= j < len(lines) and j not in used and _CODE_ROW_NO_AMOUNT.match(lines[j]) \
                        and not _TRAILING_AMOUNTS.match(lines[j]):
                    if j == i - 1:
                        out[-1] = lines[j] + " " + line
                    else:
                        out.append(lines[j] + " " + line)
                    used.add(j)
                    break
            else:
                out.append(line)
            continue
        out.append(line)
    return out


def _pick_columns(desc: str, dept_column: bool) -> tuple[str, int | None]:
    """A table row's text cells ("04/22/2026", "85025", "Complete Blood Count", "Laboratory Services", "1"):
    keeps the date, the code and the description, drops the Department / Provider cell, and returns the Qty."""
    keep, qty, text_seen = [], None, False
    for cell in (c.strip(" |") for c in desc.split("\t")):
        if not cell:
            continue
        if not text_seen and (_DATE_CELL_ANY.match(cell) or _GARBLED_DATE.match(cell + " ")):
            keep.append(cell)
        elif not text_seen and _CODE_CELL.match(cell):
            keep.append(cell)
        elif text_seen and _QTY_CELL.match(cell):
            qty = int(_QTY_CELL.match(cell)[1])
        elif not text_seen:
            keep.append(cell)
            text_seen = True
        elif not dept_column:
            keep.append(cell)               # no Department column: it's all description
    return " ".join(keep), qty


def _amount_columns(line: str) -> tuple[int, int] | None:
    """For a header row like 'Date Description Provider Charges Credits Balance': (number of amount
    columns, position of the charges column among them). None if it isn't such a header."""
    words = [w.strip(":").lower() for w in line.split()]
    if not any(w in rb.DESC_HEADERS for w in words):
        return None
    amounts = [w for w in words if w in rb.AMOUNT_HEADERS]
    charge = next((i for i, w in enumerate(amounts) if w in rb.CHARGE_HEADERS), None)
    if charge is None:
        return None
    if len(amounts) < 2:      # the other headers were misread ("Charge roe gw py"): Charges is the first amount
        return 0, 0
    return len(amounts), charge


def _charges_from_lines(pages: list[list[str]]) -> tuple[list[rb._Charge], Decimal | None]:
    charges: list[rb._Charge] = []
    total = None
    last: rb._Charge | None = None
    extra = 0
    columns = None
    has_qty = False
    qty_unit_table = False   # a "Qty  Unit price  Line total" table
    dept_column = False      # the table has a Department / Provider column next to the description
    activity = False         # inside a "Billing activity / transactions" table
    printed_date = None
    pending = None        # (charge, text) of the last line added as a continuation
    for page_no, page in enumerate(pages):
        activity = False
        for line in _rejoin_rows([ln for raw in page for ln in logical_lines(raw)]):
            header = _amount_columns(line)
            if header:
                columns, last = header, None
                has_qty = bool(re.search(r"\b(qty|quantity|units?)\b", line, re.IGNORECASE))
                qty_unit_table = bool(re.search(r"\b(unit|price|rate)\b", line, re.IGNORECASE)) and \
                    not re.search(r"qty\s*/\s*units?", line, re.IGNORECASE)
                dept_column = bool(re.search(r"\b(provider|department|dept|physician|doctor)\b", line, re.IGNORECASE))
                # "Posting Date  Transaction / Description  Amount": a history of charges and payments already
                # listed above, so nothing in it is a new charge
                activity = bool(re.search(r"\b(posting|transactions?|activity)\b", line, re.IGNORECASE))
                pending = None
                continue
            found_date = _SERVICE_DATE.search(line)
            if found_date and printed_date is None:
                printed_date = rb._parse_date(found_date[1].replace("-", "/"))
            m = _TRAILING_AMOUNTS.match(line)
            if not m or not rb._LETTERS.search(m["desc"]):
                if m is None and total is None:   # a two-column layout can put "Total charges $355.00" mid-line
                    found = _TOTAL_CHARGES_ANYWHERE.search(line)
                    if found:
                        total = rb._money(found[1])
                if m is None and _PROVIDER_NAME.search(line):
                    continue                                   # "Sonia Patel, MD" wrapped in the Provider column
                if (m is None and last is None and columns and not activity and rb._LETTERS.search(line)
                        and len(line.split()) <= 8 and not (rb.SKIP_WORDS.search(line) or _TOTAL_ROW.search(line)
                                                            or _SUBTOTAL.search(line) or "$" in line)):
                    pending = (None, line.replace("\t", " ").strip(" |"))   # may be the first line of the next row
                    continue
                if (m is None and last is not None and extra < rb.MAX_CONTINUATION and rb._LETTERS.search(line)
                        and not (rb.SKIP_WORDS.search(line) or _TOTAL_ROW.search(line) or "$" in line
                                 or _STARTS_WITH_DATE.match(line)       # a line starting with a date is a new row
                                 or len(line.split()) > 8               # a sentence under the table, not a name
                                 or (qty_unit_table and not re.search(r"[A-Za-z]{4,}", line)))):   # "BEE ame" junk
                    piece = re.sub(r"^[a-z]\s+", "", line.replace("\t", " ")).strip(" |")   # "i iral panel"
                    piece = _CREDENTIAL_END.sub("", piece).strip()   # "MD": the rest of a doctor's name
                    if not piece:
                        continue
                    last.description.append(piece)
                    pending = (last, piece)
                    extra += 1
                    continue
                if m is None:
                    last = None
                continue
            amounts = [rb._money(a) for a in re.findall(_AMOUNT, m["amts"])]
            amounts = [a for a in amounts if a is not None]
            if not amounts:
                continue
            if qty_unit_table and len(amounts) == 2:
                amount = amounts[-1]                         # Unit price, Line total: the line total
            elif len(amounts) > 1 and columns and len(amounts) == columns[0]:
                amount = amounts[columns[1]]                 # the Charges column of a multi-amount row
            elif len(amounts) > 1 and columns:
                amount = amounts[0]                         # some columns empty: Charges comes first
            else:
                amount = amounts[-1]
            desc = _NAME_BEFORE_CREDENTIAL.sub("", m["desc"]).strip(" :-")   # "Sam Doctor," (MD on the next line)
            last = None
            if amount is None or amount <= 0:
                continue
            if _SUBTOTAL.search(desc):      # "Subtotal of Charges (Page 1)": its charges are already listed
                continue
            if activity:                    # charge / payment history: the charges are already listed above
                continue
            qty_column = None
            if "\t" in desc:
                desc, qty_column = _pick_columns(desc, dept_column)
                if qty_column is not None and len(amounts) == 2:      # Qty, Unit price, Line total
                    desc, qty_column = f"{desc} {qty_column}", None
            desc = desc.replace("\t", " ")
            if _NEW_CHARGES.match(desc):    # a summary box, not a charge: the total when nothing better is printed
                if total is None:
                    total = amount
                continue
            if rb.BILLED_TOTAL.search(desc):
                total = amount
                continue
            if _TOTAL_ROW.search(desc):
                # "Total charges", or the Totals row under a charges table (its Charges column)
                if rb.TOTAL_CHARGES.search(desc) or (columns and len(amounts) > 1):
                    total = amount
                continue
            if rb.SKIP_WORDS.search(desc) or ":" in rb._QTY_IN_TEXT.sub("", desc):
                continue
            item = rb._Charge(amount=amount, page=page_no)
            item.qty_unit = None
            item.garbled = False
            qty = _QTY_UNIT.match(desc) if len(amounts) == 2 and amounts[0] > 0 else None
            if qty and int(qty["qty"]) > 0:
                item.qty_unit = (int(qty["qty"]), amounts[0], desc)   # kept only if the bill uses Qty x Unit price
                desc = qty["desc"]
            date = _LEADING_DATE.match(desc)
            text_date = _LEADING_TEXT_DATE.match(desc)
            if date:
                item.service_date = rb._parse_date(date[1].replace("-", "/"))
                desc = _DATE_RANGE_END.sub("", desc[date.end():])
            elif text_date:
                try:
                    item.service_date = rb.date(int(text_date[3]), _MONTHS[text_date[1][:3].lower()],
                                                int(text_date[2]))
                except ValueError:
                    pass
                desc = desc[text_date.end():]
            elif _GARBLED_DATE.match(desc):
                desc = _GARBLED_DATE.sub("", desc)
            if has_qty and columns and item.qty_unit is None:
                desc = _TRAILING_QTY.sub("", desc)
            desc = _CLINICIAN.sub("", desc).strip(" ,;-") or desc
            rest = _LEADING_CODE.sub("", desc)
            if pending and (not re.search(r"[A-Za-z]{4,}", rest) or rest.startswith("(")):
                # the text line just above belongs to this row: its description was misread, or it continues
                # on this line in brackets ("Surgical Pathology Exam" / "(appendix, gross & microscopic)")
                owner, piece = pending
                if owner is not None and piece in owner.description:
                    owner.description.remove(piece)
                code = _LEADING_CODE.match(desc)
                more = rest.startswith("(") and re.search(r"[A-Za-z]{4,}", rest)
                desc = (code[1] + " " if code else "") + piece + (" " + rest if more else "")
            item.description = [desc]
            item.qty_column = qty_column
            pending = None
            charges.append(item)
            last, extra = item, 0
    charges = rb._drop_group_totals(charges)
    for ch in charges:
        text = " ".join(ch.description)
        found = rb._CODE_IN_TEXT.search(text)
        if found:
            ch.code = found[1].upper()
            ch.description = [rb._CODE_IN_TEXT.sub("", text)]
        else:
            found = _LEADING_CODE.match(text)     # "99203 Urgent care visit": the CPT/HCPCS column
            if found:
                raw = found[1].upper()
                ch.code = raw
                ch.garbled = not re.fullmatch(r"\d{5}|[A-V]\d{4}|0\d{3}", raw)
                ch.description = [text[found.end():]]
    # "Qty  Unit price  Line total": used when the table says so, or when most rows multiply out
    rows = [c for c in charges if c.qty_unit]
    exact = [c for c in rows if abs(c.qty_unit[0] * c.qty_unit[1] - c.amount) <= Decimal("0.01")]
    use_qty = qty_unit_table or (len(exact) >= 2 and len(exact) * 2 >= len(rows))
    for c in rows:
        if not use_qty:                           # not that kind of table: put the number back in the name
            first = c.description[0]
            c.description[0] = first + " " + str(c.qty_unit[0]) if first else first
            c.qty_unit = None
    if printed_date and not any(c.service_date for c in charges):   # "Date of Service: 01/28/2025" up top
        for c in charges:
            c.service_date = printed_date
    return charges, total


_NAME_IN_HEADER = re.compile(
    r"\b((?:[A-Z][a-z][\w'&-]*\s+){1,5}(?:Community Hospital|Hospital|Medical Center|Medical Group|Health Center|"
    r"Urgent Care(?: Network| Center)?|Pediatrics|Clinic|Health System|Physicians))\b")
_KIND_START = re.compile(r"^(?:Community Hospital|Hospital|Medical Center|Medical Group|Health Center|"
                         r"Urgent Care(?: Network| Center)?|Pediatrics|Clinic|Health System|Physicians)\b")
_LOCATION_LABEL = re.compile(r"(?:^|\s)(?:Service Location|Location|Facility):\s*(?P<name>.+?)\s*$", re.IGNORECASE)


def _facility(pages: list[list[str]]) -> str | None:
    """The hospital or practice name: a labeled line, the name printed at the top, or 'Service Location:'."""
    lines = [ln for page in pages for raw in page for ln in logical_lines(raw)]
    for line in lines:
        for pattern in rb._FACILITY:
            m = pattern.match(line)
            if m and rb._LETTERS.search(m["name"]) and not re.search(r"\d{3}", m["name"]):
                return m["name"].strip(" ,;-")[:100]
    found: list[str] = []
    for page in pages:                                     # the letterhead of each page
        top = [[clean_line(c) for c in _GAP.split(raw) if c.strip()] for raw in page[:8]]
        for i, cells in enumerate(top):
            for cell in cells:
                m = _NAME_IN_HEADER.search(cell)
                if m:
                    found.append(m[1].strip())
                    continue
                start = re.search(r"((?:[A-Z][a-z]+ ){0,3}[A-Z][a-z]+)$", cell)   # "Westbrook Regional" ...
                for nxt in top[i + 1:i + 3]:                                       # ... "Medical Center" below
                    if start and nxt and _KIND_START.match(nxt[0]):
                        found.append(start[1] + " " + _KIND_START.match(nxt[0])[0])
    if found:
        return max(set(found), key=found.count)[:100]
    for line in lines:
        m = _LOCATION_LABEL.search(line)
        if m and _NAME_IN_HEADER.search(m["name"]) and not re.search(r"\d{3}", m["name"]):
            return _NAME_IN_HEADER.search(m["name"])[1].strip()[:100]
    return None


def read_photo_text(pages: list[list[str]]) -> rb.RealBill | None:
    """The bill's charges from the text of up to MAX_PAGES photos, or None if no charges were found."""
    from app.engine.photo_codes import fix_code

    charges, total = _charges_from_lines(pages[:MAX_PAGES])
    if not charges:
        return None
    lines = []
    for n, ch in enumerate(charges, start=1):
        description = rb._clean(ch.description) or "Charge"
        qty, unit = (Decimal(ch.qty_unit[0]), ch.qty_unit[1]) if getattr(ch, "qty_unit", None) else (Decimal(1), ch.amount)
        q = getattr(ch, "qty_column", None)
        if not getattr(ch, "qty_unit", None) and q and q > 1 and (ch.amount / q) == (ch.amount / q).quantize(Decimal("0.01")):
            qty, unit = Decimal(q), (ch.amount / q).quantize(Decimal("0.01"))   # "Qty 3, Charges $96.00" = 3 x $32.00
        lines.append(LineItem(line_no=n, code=fix_code(ch.code, description, getattr(ch, "garbled", False)),
                              description=description, quantity=qty, unit_price=unit, line_total=ch.amount))
    summed = sum((ln.line_total for ln in lines), Decimal("0"))
    service_date = next((c.service_date for c in charges if c.service_date), None)
    bill = Bill(bill_id="PHOTO", lines=lines, stated_subtotal=total if total is not None else summed,
                date_of_service=service_date)
    from app.engine.payments import extract_payments   # local import: payments.py imports this module
    bill.payments = extract_payments(pages[:MAX_PAGES], bill.stated_subtotal)
    return rb.RealBill(bill=bill, has_total=total is not None, from_table=False, provider_name=_facility(pages))