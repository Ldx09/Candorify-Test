"""Reads the totals from an insurance EOB (Explanation of Benefits): amount billed, the plan's allowed
amount, what the plan paid, and what the patient may owe, plus the service dates.

EOBs come in two common shapes, and both are handled:
    key/value lines:  "Amount billed $1,000.00" / "Your plan paid $700.00" / "What you owe $100.00"
    a table:          "Amount Billed  Allowed  Plan Paid  Deductible  Copay  What You Owe" then claim rows
                      and usually a "Total" row with the same number of amounts.
A "Total" line or row wins; otherwise single claim lines are added up. If "what you owe" isn't printed,
deductible + copay + coinsurance + not covered is used. Works on PDF text and on text read from photos.
No names, member IDs or claim numbers are kept. Deterministic, no AI.
"""
import re
from datetime import date
from decimal import Decimal

import pdfplumber

from app.engine import real_bills as rb
from app.engine.photo_bills import _AMOUNT, _TRAILING_AMOUNTS, clean_line
from app.models.eob import EobSummary

# One pattern, so a table header can be split into columns in the order they appear.
_FIELDS = re.compile(
    r"(?P<you_owe>what you owe|amount you (?:may )?owe|you (?:may )?owe|your share|your (?:total )?responsibility|"
    r"patient responsibility|member responsibility|your (?:total )?cost|you pay)"
    r"|(?P<plan_paid>(?:amount )?(?:your )?plan paid|(?:amount )?paid by (?:your )?(?:plan|insurance)|plan payment|"
    r"insurance paid|ins\. paid|we paid|"
    r"benefits? paid|paid to provider|plan pays)"
    r"|(?P<allowed>allowed(?: amount)?|member rate|approved amount|negotiated (?:rate|amount)|plan allowance|network rate)"
    r"|(?P<billed>amount billed|billed amount|billed charges|amount charged|provider charged|provider billed|"
    r"total charges|billed|charges)"
    r"|(?P<part>deductible|co-?pay(?:ment)?|co-?insurance|not covered|not payable)",
    re.IGNORECASE)
MAIN = ("billed", "allowed", "plan_paid", "you_owe")
_DATE_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
_DATE_TEXT = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? (\d{1,2}),? (\d{4})\b", re.I)
_MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                        "dec"), start=1)}
_NOT_SERVICE = re.compile(r"statement date|processed|issue date|issued|printed|mailed|received|date of birth|"
                          r"\bdob\b|effective|member since|due date|payment|\beft\b|member services", re.I)
_SERVICE = re.compile(r"service|\bdos\b|date of visit|visit date|dates? of care", re.I)


def _dates(line: str) -> list[date]:
    found = []
    for m in _DATE_NUM.finditer(line):
        month, day, year = int(m[1]), int(m[2]), int(m[3])
        year = year + 2000 if year < 100 else year
        try:
            found.append(date(year, month, day))
        except ValueError:
            pass
    for m in _DATE_TEXT.finditer(line):
        try:
            found.append(date(int(m[3]), _MONTHS[m[1][:3].lower()], int(m[2])))
        except ValueError:
            pass
    return found


def _field(text: str) -> str | None:
    m = _FIELDS.search(text)
    return m.lastgroup if m else None


def read_eob_lines(pages: list[list[str]]) -> EobSummary | None:
    """The EOB totals from its text lines, or None if no insurance amounts were found."""
    kv_total: dict[str, list[Decimal]] = {}
    kv_single: dict[str, list[Decimal]] = {}
    kv_parts: list[Decimal] = []
    table_total: dict[str, Decimal] = {}
    table_rows: dict[str, list[Decimal]] = {}
    dates: list[date] = []
    columns: list[str] | None = None

    for page in pages:
        for raw in page:
            line = clean_line(raw)
            if not line:
                continue
            m = _TRAILING_AMOUNTS.match(line)
            if not m:   # maybe a table header
                names = [h.lastgroup for h in _FIELDS.finditer(line)]
                if len(names) >= 3 and any(n in MAIN for n in names):
                    columns = [n if n != "part" else f"part_{i}" for i, n in enumerate(names)]
                elif _SERVICE.search(line) and not _NOT_SERVICE.search(line):
                    dates.extend(_dates(line))
                continue
            desc = m["desc"].strip(" :-|")
            amounts = [a for a in (rb._money(x) for x in re.findall(_AMOUNT, m["amts"])) if a is not None]
            if not _NOT_SERVICE.search(line) and (columns or _SERVICE.search(line)):
                dates.extend(_dates(desc))
            if columns and len(amounts) == len(columns):   # a claim row or the Total row of the table
                target_total = bool(re.search(r"\btotal", desc, re.I))
                for name, amount in zip(columns, amounts):
                    if target_total:
                        table_total[name] = abs(amount)
                    else:
                        table_rows.setdefault(name, []).append(abs(amount))
                continue
            if len(amounts) != 1 or not rb._LETTERS.search(desc):
                continue
            name = _field(desc)
            if name is None:
                continue
            amount = abs(amounts[0])
            if name == "part":
                kv_parts.append(amount)
            else:
                (kv_total if re.search(r"\btotal", desc, re.I) else kv_single).setdefault(name, []).append(amount)

    def pick(name: str) -> Decimal | None:
        if name in table_total:
            return table_total[name]
        if kv_total.get(name):
            return max(kv_total[name])
        if table_rows.get(name):
            return sum(table_rows[name], Decimal("0"))
        if kv_single.get(name):
            return sum(kv_single[name], Decimal("0"))
        return None

    eob = EobSummary(billed=pick("billed"), allowed=pick("allowed"), plan_paid=pick("plan_paid"),
                     you_owe=pick("you_owe"))
    if eob.you_owe is None:   # not printed: add up the patient's parts (deductible, copay, coinsurance, ...)
        parts = [v for k, v in table_total.items() if k.startswith("part_")]
        if not parts:
            parts = [sum(v, Decimal("0")) for k, v in table_rows.items() if k.startswith("part_")]
        parts = parts or kv_parts
        if parts:
            eob.you_owe = sum(parts, Decimal("0"))
    if eob.billed is not None:   # nothing on an EOB can be more than what was billed: a misread amount
        for name in ("allowed", "plan_paid", "you_owe"):
            if getattr(eob, name) is not None and getattr(eob, name) > eob.billed + Decimal("0.01"):
                setattr(eob, name, None)
    if eob.plan_paid is None and eob.you_owe is None:
        return None
    eob.service_dates = sorted(set(dates))[:31]
    return eob


def read_eob_pdf(path) -> EobSummary | None:
    with pdfplumber.open(path) as pdf:
        pages = [(page.extract_text() or "").splitlines() for page in pdf.pages]
    return read_eob_lines(pages)