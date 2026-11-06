"""Marked-up bill. One PDF with three parts:
  1. the patient's original bill, unchanged
  2. the same bill with every flagged charge highlighted and numbered
  3. a last page listing what to ask about

Privacy: Candorify never stores PDFs. The browser sends the original PDF again only for this request;
it is read and marked up in memory and the result is streamed straight back. Nothing is written to disk.

Two ways to build it:
  * mark_up_original(): highlights the rows on the patient's own PDF. Used when the PDF's charge rows
    can be matched, in order, to the charges we have stored for this bill.
  * rebuild_marked_up(): if there is no PDF, or its rows can't be matched (different layout, edited
    charges, wrong file), a clean statement is rebuilt from the stored charges and marked up instead.
Nothing here decides what is an error: it only draws the flags the check engine and the answers produced.
"""
import io
import re
from dataclasses import dataclass
from decimal import Decimal

import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from app.engine.models import Flag
from app.models.bill import Bill
from app.models.line_item import format_qty

FLAG_TITLES = {
    "duplicate_line": "Possible duplicate charge",
    "line_math": "Line total doesn't match quantity x price",
    "subtotal_mismatch": "Total doesn't match the charges",
    "answer_mismatch": "Doesn't match what you told us",
}
HIGHLIGHT = (1.0, 0.82, 0.25)   # marker yellow
BADGE = (0.12, 0.23, 0.18)      # Candorify forest green
_ACCOUNT = re.compile(r"Account #:\s*(\S+)")
_LINE = re.compile(r"^(\S+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+\$?(-?[\d,]+\.\d{2})\s+\$?(-?[\d,]+\.\d{2})$")
_TOTAL = re.compile(r"^Total charges\s+\$?(-?[\d,]+\.\d{2})$", re.IGNORECASE)


@dataclass
class Box:
    page: int
    x0: float
    top: float
    x1: float
    bottom: float


def _money(x: Decimal) -> str:
    return f"${x:,.2f}"


def _rows(page) -> list[tuple[str, float, float, float, float]]:
    """Text lines on a page with their bounding box (pdfplumber coordinates: top-left origin)."""
    rows: list[list[dict]] = []
    for w in sorted(page.extract_words(keep_blank_chars=False), key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1][0]["top"] - w["top"]) <= 3:
            rows[-1].append(w)
        else:
            rows.append([w])
    out = []
    for ws in rows:
        ws.sort(key=lambda w: w["x0"])
        out.append((" ".join(w["text"] for w in ws), min(w["x0"] for w in ws), min(w["top"] for w in ws),
                    max(w["x1"] for w in ws), max(w["bottom"] for w in ws)))
    return out


def locate_rows(pdf_bytes: bytes, bill: Bill, account: str | None) -> tuple[dict[int, Box], Box | None] | None:
    """Finds each stored charge's row in the PDF. Returns ({line_no: box}, total_box), or None if the
    PDF's charges don't match the stored bill exactly (then the rebuilt version is used)."""
    found: dict[str, list[tuple[re.Match, Box]]] = {}
    totals: dict[str, Box] = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for p, page in enumerate(pdf.pages):
            current = None
            for text, x0, top, x1, bottom in _rows(page):
                if m := _ACCOUNT.search(text):
                    current = m[1]
                    continue
                if current is None:
                    continue
                box = Box(p, x0, top, x1, bottom)
                if _TOTAL.match(text):
                    totals[current] = box
                elif m := _LINE.match(text):
                    found.setdefault(current, []).append((m, box))
    if not found:
        return None
    if account and account.upper() in {a.upper() for a in found}:
        key = next(a for a in found if a.upper() == account.upper())
    elif len(found) == 1:
        key = next(iter(found))
    else:
        return None
    rows = found[key]
    if len(rows) != len(bill.lines):
        return None
    boxes = {}
    for line, (m, box) in zip(bill.lines, rows):
        if m[1].upper() != line.code.upper() or Decimal(m[5].replace(",", "")) != line.line_total:
            return None  # the PDF doesn't match what we have stored (edited charges or another bill)
        boxes[line.line_no] = box
    return boxes, totals.get(key)


def _numbered(flags: list[Flag]) -> list[tuple[int, Flag]]:
    return list(enumerate(flags, start=1))


def _targets(flag: Flag) -> list[int]:
    return list(flag.line_numbers or ([flag.line_no] if flag.line_no else []))


def _draw_mark(c: canvas.Canvas, page_h: float, page_w: float, box: Box, numbers: list[int]) -> None:
    """Yellow highlight across the row and a numbered badge in the left margin."""
    pad = 2.5
    y = page_h - box.bottom - pad
    h = box.bottom - box.top + 2 * pad
    c.saveState()
    c.setFillColorRGB(*HIGHLIGHT, alpha=0.32)
    c.setStrokeColorRGB(*HIGHLIGHT, alpha=0.9)
    c.rect(box.x0 - 4, y, min(page_w - 20, box.x1 + 4) - (box.x0 - 4), h, fill=1, stroke=1)
    c.setFillAlpha(1)
    c.setStrokeAlpha(1)
    label = ",".join(str(n) for n in numbers)
    r = 7 + 2.6 * max(0, len(label) - 1)
    cx = max(r + 4, box.x0 - r - 8)
    cy = y + h / 2
    c.setFillColorRGB(*BADGE)
    c.roundRect(cx - r, cy - 7, 2 * r, 14, 7, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(cx, cy - 2.8, label)
    c.restoreState()


def _summary_pages(c: canvas.Canvas, bill: Bill, flags: list[Flag], rebuilt: bool,
                   has_original: bool = False) -> None:
    """Last page(s): the numbered list of things to ask about."""
    w, h = letter
    x, y = 50, h - 60

    def new_page():
        nonlocal y
        c.showPage()
        y = h - 60

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "Things to ask about on this bill")
    y -= 22
    c.setFont("Helvetica", 9.5)
    intro = ""
    if has_original:
        intro = ("This file has your original bill (unchanged) first, then the same charges marked up, then this "
                 "list. ")
    intro += ("The highlighted rows were flagged by Candorify. A flag means it's worth asking the billing office "
              "about it. It is not proof of an error.")
    if rebuilt and has_original:
        intro += (" Your bill's layout couldn't be matched, so the marked-up charges are a reprint of your bill's "
                  "charges.")
    elif rebuilt:
        intro += (" Your original PDF's layout couldn't be matched, so the charges were reprinted from your bill "
                  "on the previous page(s).")
    for part in simpleSplit(intro, "Helvetica", 9.5, w - 2 * x):
        c.drawString(x, y, part)
        y -= 13
    y -= 8
    by_line = {ln.line_no: ln for ln in bill.lines}
    for n, f in _numbered(flags):
        lines = _targets(f)
        where = ("Total" if f.rule == "subtotal_mismatch"
                 else "Line " + ", ".join(str(ln) for ln in lines) if lines else "Bill")
        first = by_line.get(lines[0]) if lines else None
        detail = f" - {first.code} {first.description}" if first and f.rule != "subtotal_mismatch" else ""
        body = f.letter_text if f.rule == "answer_mismatch" and f.letter_text else f.message
        block = simpleSplit(body, "Helvetica", 9.5, w - 2 * x - 24)
        title = f"{FLAG_TITLES.get(f.rule, 'Flagged')} ({where}{detail})"
        title_lines = simpleSplit(title, "Helvetica-Bold", 10.5, w - 2 * x - 24)  # wraps instead of cutting off
        if y - 15 * len(title_lines) - 13 * len(block) < 60:
            new_page()
        c.setFillColorRGB(*BADGE)
        c.roundRect(x, y - 3.5, 16, 14, 7, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + 8, y + 0.5, str(n))
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 10.5)
        for part in title_lines:
            c.drawString(x + 24, y, part)
            y -= 15
        c.setFont("Helvetica", 9.5)
        for part in block:
            c.drawString(x + 24, y, part)
            y -= 13
        y -= 10
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.35, 0.36, 0.32)
    c.drawString(x, 40, "Marked up by Candorify. Your PDF was not stored. Candorify is not a lawyer or a medical "
                        "billing service.")
    c.showPage()


def mark_up_original(pdf_bytes: bytes, bill: Bill, flags: list[Flag], boxes: dict[int, Box],
                     total_box: Box | None) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    marks: dict[int, list[tuple[Box, list[int]]]] = {}
    per_line: dict[int, list[int]] = {}
    total_nums: list[int] = []
    for n, f in _numbered(flags):
        if f.rule == "subtotal_mismatch":
            total_nums.append(n)
        for ln in _targets(f):
            per_line.setdefault(ln, []).append(n)
    for ln, nums in per_line.items():
        if ln in boxes:
            marks.setdefault(boxes[ln].page, []).append((boxes[ln], nums))
    if total_nums and total_box:
        marks.setdefault(total_box.page, []).append((total_box, total_nums))

    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(pdf_bytes)).pages:   # part 1: the original, untouched
        writer.add_page(page)
    for i, page in enumerate(reader.pages):              # part 2: the same pages, marked up
        if i in marks:
            pw, ph = float(page.mediabox.width), float(page.mediabox.height)
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(pw, ph))
            for box, nums in marks[i]:
                _draw_mark(c, ph, pw, box, nums)
            c.save()
            page.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0])
        writer.add_page(page)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    _summary_pages(c, bill, flags, rebuilt=False, has_original=True)
    c.save()
    for page in PdfReader(io.BytesIO(buf.getvalue())).pages:   # part 3: what to ask about
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def rebuild_marked_up(bill: Bill, flags: list[Flag], label: str | None, original: bytes | None = None) -> bytes:
    """Reprints the stored charges as a simple statement, marks it up, and adds the summary page."""
    w, h = letter
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    per_line: dict[int, list[int]] = {}
    total_nums = []
    for n, f in _numbered(flags):
        if f.rule == "subtotal_mismatch":
            total_nums.append(n)
        for ln in _targets(f):
            per_line.setdefault(ln, []).append(n)

    y = 0.0

    def header():
        nonlocal y
        c.setFont("Helvetica-Bold", 15)
        c.drawString(60, h - 55, "Itemized charges (reprinted by Candorify)")
        c.setFont("Helvetica", 9.5)
        meta = f"Bill: {label or '-'}"
        if bill.date_of_service:
            meta += f"   Date of service: {bill.date_of_service.strftime('%m/%d/%Y')}"
        c.drawString(60, h - 72, meta)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(60, h - 100, "Line")
        c.drawString(88, h - 100, "Code")
        c.drawString(138, h - 100, "Description")
        c.drawRightString(410, h - 100, "Qty")
        c.drawRightString(480, h - 100, "Unit price")
        c.drawRightString(552, h - 100, "Line total")
        y = h - 120

    def row(text_cols, top_y, numbers):
        line_top = h - top_y - 10
        box = Box(0, 60, line_top, 552, line_top + 12)
        if numbers:
            _draw_mark(c, h, w, box, numbers)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 9.5)
        line_no, code, desc, qty, unit, total = text_cols
        c.drawString(60, top_y, line_no)
        c.drawString(88, top_y, code)
        desc_lines = simpleSplit(desc, "Helvetica", 9.5, 370 - 138)
        c.drawString(138, top_y, desc_lines[0] + ("..." if len(desc_lines) > 1 else "") if desc_lines else "")
        c.drawRightString(410, top_y, qty)
        c.drawRightString(480, top_y, unit)
        c.drawRightString(552, top_y, total)

    header()
    for ln in bill.lines:
        if y < 80:
            c.showPage()
            header()
        row((str(ln.line_no), ln.code, ln.description, format_qty(ln.quantity), _money(ln.unit_price),
             _money(ln.line_total)), y, per_line.get(ln.line_no, []))
        y -= 20
    y -= 6
    row(("", "", "Total charges", "", "", _money(bill.stated_subtotal)), y, total_nums)
    c.showPage()
    _summary_pages(c, bill, flags, rebuilt=True, has_original=original is not None)
    c.save()
    if original is None:
        return buf.getvalue()
    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(original)).pages:   # the original, untouched, goes first
        writer.add_page(page)
    for page in PdfReader(io.BytesIO(buf.getvalue())).pages:
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def marked_up_pdf(bill: Bill, flags: list[Flag], label: str | None, pdf_bytes: bytes | None) -> tuple[bytes, bool]:
    """Returns (pdf, marked_on_original). Never raises for a PDF that can't be matched: it falls back."""
    if pdf_bytes:
        try:
            located = locate_rows(pdf_bytes, bill, label)
            if located:
                return mark_up_original(pdf_bytes, bill, flags, *located), True
        except Exception:  # unusual PDF: fall through to the reprinted version
            pass
        try:  # still include their original pages in front of the reprint
            return rebuild_marked_up(bill, flags, label, original=pdf_bytes), False
        except Exception:  # the PDF can't even be copied: reprint only
            pass
    return rebuild_marked_up(bill, flags, label), False