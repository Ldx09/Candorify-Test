"""Builds data/demo_bills.pdf from data/demo_bills.csv, one itemized statement per page, in the same
layout as the provided synthetic bills PDF (so the PDF loader can read it back).

Needs reportlab (only for this script):   pip install reportlab
Run from the backend folder:              python -m scripts.make_demo_pdf
"""
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.engine.loader import load_bills

DATA = Path(__file__).resolve().parent.parent / "data"


def money(x) -> str:
    return f"${x:,.2f}"


def main(src: Path = DATA / "demo_bills.csv", out: Path = DATA / "demo_bills.pdf") -> None:
    bills = load_bills(src)
    c = canvas.Canvas(str(out), pagesize=letter)
    for bill in bills:
        y = 740
        def line(text, size=10, bold=False):
            nonlocal y
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
            c.drawString(50, y, text)
            y -= 18
        line("Riverside General Hospital", 14, bold=True)
        line("Itemized Statement of Charges | 123 Medical Center Dr, Anytown, USA")
        line("Patient: [Patient Name] Statement date: 09/28/2026")
        line(f"Account #: {bill.bill_id} Provider NPI: 1000000000")
        dos = bill.date_of_service.strftime("%m/%d/%Y") if bill.date_of_service else ""
        line(f"Date of service: {dos} Page: 1 of 1")
        y -= 6
        line("Code Description Qty Unit price Line total", bold=True)
        for ln in bill.lines:
            qty = format(ln.quantity.normalize(), "f")
            line(f"{ln.code} {ln.description} {qty} {money(ln.unit_price)} {money(ln.line_total)}")
        line(f"Total charges {money(bill.stated_subtotal)}", bold=True)
        y -= 10
        line("This is a synthetic bill generated for testing Candorify. It does not represent a real patient or real charges.", 8)
        c.showPage()
    c.save()
    print(f"Wrote {len(bills)} bills -> {out}")


if __name__ == "__main__":
    main(*(Path(a) for a in sys.argv[1:3]))