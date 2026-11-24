"""Photo bills: text read on the phone, with the usual phone-reading slips. FAKE data only.
Run: pytest -q tests/test_photo_bills.py"""
from datetime import date
from decimal import Decimal

from app.engine.checks import run_checks
from app.engine.photo_bills import clean_line, logical_lines, read_photo_text

D = Decimal

# The text a phone reads from a statement with a Charges/Payments/Adjustments/Patient Amount table
STATEMENT = [
    "Sample Clinic Billing Services Medical Billing Statement",
    "Summary of Charges",
    "Service Date(s) Description Provider Charges Payments Adjustments Patient",
    "Amount",
    "Dec 03, 2025 Pediatric Office Visit, Established (Level 3) Jane Q. Doctor, MD 275.00 175.00 70.00 30.00",
    "Dec 03, 2025 Influenza Vaccination (IIV4) Jane Q. Doctor, MD 45.00 45.00 0.00 0.00",
    "Dec 03, 2025 Vaccine Administration Jane Q. Doctor, MD 35.00 35.00 0.00 0.00 |",   # table border read as "|"
    "Totals $355.00 $255.00 $70.00 $30.00",
    "Insurance Payments -$255.00",
    "Insurance Adjustments (Contractual) -$70.00",
    "Remaining Balance Due $30.00",
]


def test_table_with_text_dates_doctor_names_and_totals_row():
    r = read_photo_text([STATEMENT])
    lines = [(ln.description, ln.line_total) for ln in r.bill.lines]
    assert lines == [("Pediatric Office Visit, Established (Level 3)", D("275.00")),
                     ("Influenza Vaccination (IIV4)", D("45.00")),
                     ("Vaccine Administration", D("35.00"))]
    assert r.bill.stated_subtotal == D("355.00") and r.has_total            # the Totals row, not a charge
    assert r.bill.date_of_service == date(2025, 12, 3)
    assert r.bill.payments.insurance_paid == D("255.00") and r.bill.payments.balance_due == D("30.00")


def test_stray_border_characters_after_amounts():
    assert clean_line("Vaccine Administration 35.00 0.00 |") == "Vaccine Administration 35.00 0.00"
    assert clean_line("Lab work 12.50]") == "Lab work 12.50"
    assert clean_line("Refund (85.00)") == "Refund (85.00)"                 # a negative amount keeps its ")"


def test_total_charges_in_the_middle_of_a_line():
    pages = [["Office visit 100.00", "Lab 50.00",
              "Total Charges $150.00 Your responsibility for this visit is $30.00, which includes"]]
    r = read_photo_text(pages)
    assert r.bill.stated_subtotal == D("150.00") and r.has_total


# ---- Phone text with the wide column gaps kept (4 spaces), like photo.js sends. FAKE bills. ----
G = "    "   # a wide gap between two columns

URGENT_CARE = [
    "Sample Urgent Care Network" + G + "Statement Date:" + G + "02/14/2025",
    "Patient Name:" + G + "Test Person" + G + "Date of Service (DOS):" + G + "01/28/2025",
    "Primary Insurance" + G + "Prior Balance:" + G + "$25.00",
    "Test Health Plan" + G + "New Charges (This Visit):" + G + "$365.00",
    "Member ID: X000" + G + "Insurance Payments/Adjustments:" + G + "-$307.50",
    "CPT/HCPCS Service Description" + G + "Qty" + G + "Charge" + G + "roe" + G + "gw" + G + "py",   # misread headers
    "| 99203 Urgent care visit, new patient (level 3)" + G + "1" + G + "$21000 =~ -$168.00 $42.00" + G + "$000 $0.00",
    "| 87804" + G + "Influenza A/B antigen test (POCT)" + G + "1" + G + "$45.00" + G + "-$27.00" + G + "-$18.00" + G + "$0.00",
    "87070" + G + "Throat culture" + G + "1" + G + "$30.00" + G + "-$18.00" + G + "-$12.00" + G + "$0.00",
    "J1100" + G + "Dexamethasone, 4 mg (IM)" + G + "1" + G + "$25.00" + G + "-$15.00" + G + "-$10.00" + G + "$10.00",
    "k  Totals (This Visit)" + G + "$310.00" + G + "-$228.00" + G + "-$82.00" + G + "$10.00",
    "12/20/2024" + G + "Prior balance (unpaid from an earlier visit)" + G + "$25.00",
    "01/28/2025" + G + "Payment — Credit Card" + G + "-$10.00",
    "02/03/2025" + G + "Insurance Payment — Test Health Plan" + G + "-$146.00",
    "02/03/2025" + G + "Insurance Adjustment — Contractual Allowance" + G + "-$82.00",
    "Amount Due:" + G + "$97.00",
]


def test_misread_headers_dropped_dots_codes_qty_and_prior_balance():
    r = read_photo_text([URGENT_CARE])
    assert [(ln.code, ln.line_total) for ln in r.bill.lines] == [
        ("99203", D("210.00")), ("87804", D("45.00")), ("87070", D("30.00")), ("J1100", D("25.00"))]
    assert r.bill.lines[2].description == "Throat culture"          # the Qty "1" is not part of the name
    assert r.bill.stated_subtotal == D("310.00")
    assert r.bill.date_of_service == date(2025, 1, 28)               # from "Date of Service (DOS):"
    assert r.provider_name == "Sample Urgent Care Network"
    p = r.bill.payments
    assert (p.insurance_paid, p.adjustments, p.patient_paid) == (D("146.00"), D("82.00"), D("10.00"))
    assert (p.prior_balance, p.balance_due) == (D("25.00"), D("97.00"))
    # 310 + 25 earlier balance - 146 - 82 - 10 = 97: adds up, so no payment flag
    assert "payment_mismatch" not in [f.rule for f in run_checks(r.bill).flags]


HOSPITAL = [
    "Sample Community Hospital" + G + "Patient Billing Statement",
    "Date" + G + "Service Description" + G + "Charges" + G + "Credits" + G + "Adjustments" + G + "Balance",
    "02/20/2025" + G + "Office Visit — Family Medicine (Established Patient)" + G + "265.00" + G + "—" + G + "-132.50" + G + "132.50",
    "02-20-2025" + G + "Hemoglobin A1c (Lab)" + G + "62.00" + G + "—" + G + "-24.80" + G + "37.20",
    "02/20/2025" + G + "Specimen Collection (Venipuncture)" + G + "18.00" + G + "-18.00" + G + "—" + G + "0.00",
    "Total for This Statement" + G + "$345.00" + G + "-$18.00" + G + "-$157.30" + G + "$169.70",
    "This statement lists outpatient services." + G + "Balance Due:" + G + "$169.70",
]


def test_dash_empty_cells_dash_dates_and_totals_row_payments():
    r = read_photo_text([HOSPITAL])
    assert [ln.line_total for ln in r.bill.lines] == [D("265.00"), D("62.00"), D("18.00")]
    assert r.bill.stated_subtotal == D("345.00")
    assert r.bill.date_of_service == date(2025, 2, 20)
    assert r.provider_name == "Sample Community Hospital"
    p = r.bill.payments
    assert (p.adjustments, p.other_payments, p.balance_due) == (D("157.30"), D("18.00"), D("169.70"))
    assert run_checks(r.bill).flags == []


def test_two_column_lines_are_split_and_table_rows_are_not():
    assert logical_lines("Insurance Payments" + G + "-$255.00" + G + "a $30.00 copay. Please pay by") == [
        "Insurance Payments -$255.00", "a $30.00 copay. Please pay by"]
    assert logical_lines("01/28/2025" + G + "Insurance Payment — Plan" + G + "-$520.00 |  |" + G + "New Charges:" + G + "$892.00") == [
        "01/28/2025 Insurance Payment - Plan -$520.00", "New Charges: $892.00"]
    row = "01/15/2025" + G + "99213" + G + "Office visit" + G + "$185.00" + G + "$110.00" + G + "$35.00"
    assert logical_lines(row) == ["01/15/2025\t99213\tOffice visit\t$185.00\t$110.00\t$35.00"]   # a tab per column
    

def test_doctor_names_garbled_rows_and_summary_box_total():
    lines = [
        "Sample Pediatrics" + G + "Patient Account Statement",
        "Total Charges:" + G + "$397.00",
        "| Dateof Service  CPT/Code" + G + "Description" + G + "Provider" + G + "Charges" + G + "even  [-TCe",
        "01/15/2025" + G + "99213" + G + "Office visit, established patient = Dr. K. Doe, M.D." + G + "$185.00" + G + "$110.00" + G + "$35.00" + G + "$40.00",
        "i" + G + "iral panel",
        "01/15/2025" + G + "87631 | (oui" + G + "Dr.K.Doe, MD. | ¢9200 $50.00" + G + "$22.00 $20.00",
        "o1s202s | oeo72 | Additional PPE | pr. K_Doe, MD. | $120.00" + G + "$0.00" + G + "$000 $12000 |",
    ]
    r = read_photo_text([lines])
    got = [(ln.code, ln.description, ln.line_total) for ln in r.bill.lines]
    assert got[0] == ("99213", "Office visit, established patient", D("185.00"))
    assert got[1][1:] == ("iral panel", D("92.00"))       # the line above a misread row is its name
    assert got[2][1:] == ("Additional PPE", D("120.00"))   # no garbled date, code or doctor name left
    assert r.bill.stated_subtotal == D("397.00")


def test_cleanup_of_phone_slips_in_amounts():
    assert clean_line("Visit 1 $21000 $000") == "Visit 1 $210.00 $0.00"
    assert clean_line("Lab ¢45.00 $1O5.00") == "Lab $45.00 $105.00"
    assert clean_line("Visit 265.00 - -132.50 132.50") == "Visit 265.00 -132.50 132.50"