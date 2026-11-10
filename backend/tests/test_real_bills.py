"""Real-world bill layouts (hospital summary + doctor statement), built here with FAKE data.
Run: pytest -q tests/test_real_bills.py"""
import io
import os
import tempfile
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

import server
from app.engine.checks import run_checks
from app.engine.code_matching import match_code
from app.engine.real_bills import read_real_bill
from app.models.bill import Bill

HOSPITAL_LINES = [
    ("Pharmacy - General Classification", "$933.08"),
    ("Pharmacy - IV Solutions", "$0.02"),
    ("IV Therapy - General Classification", "$707.00"),
    ("Medical/Surgical Supplies and Devices - Sterile Supply", "$5,017.16"),
    ("Laboratory - General Classification", "$120.00"),
    ("Laboratory - Chemistry", "$864.00"),
    ("Laboratory - Immunology", "$728.00"),
    ("Laboratory - Hematology", "$400.00"),
    ("Laboratory Pathology - Histology", "$395.00"),
    ("Operating Room Services - General Classification", "$13,670.00"),
    ("Anesthesia - General Classification", "$3,205.00"),
    ("Emergency Room - General Classification", "$5,249.00"),
    ("Pharmacy - Drugs Requiring Detailed Coding", "$165.30"),
    ("Recovery Room - General Classification", "$5,327.00"),
]


def hospital_pdf(total="$36,780.56", lines=HOSPITAL_LINES) -> bytes:
    """Same layout as a hospital 'patient statement' + 'itemized account detail' (fake patient)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 740
    for text in ["Sample Health PATIENT STATEMENT", "Statement Date: 09/23/2026", "Guarantor Name: JANE TEST",
                 "Account Number: HAR-0000000001", "Total Charges: $36,780.56", "Adjustments: -$5,741.45",
                 "Payments Received: -$30,489.11", "Total Amount Due: $550.00",
                 "Pay as little as $69.00 / month for 8 months.", "PAY NOW IN FULL", "$550.00"]:
        c.drawString(56, y, text)
        y -= 18
    c.showPage()
    c.drawString(56, 740, "Sample Health ITEMIZED ACCOUNT DETAIL")
    c.drawString(53, 700, "Description / Service Classification")
    c.drawString(451, 700, "Amount")
    y = 680
    for desc, amount in lines:
        c.drawString(53, y, desc)
        c.drawRightString(542, y, amount)
        y -= 21
    for desc, amount in [("Total Hospital Charges", total), ("Insurance Adjustments", "-$5,741.45"),
                         ("Insurance Payments", "-$30,489.11"), ("Overall Patient Responsibility", "$550.00")]:
        c.drawString(53, y, desc)
        c.drawRightString(542, y, amount)
        y -= 21
    c.drawString(53, y - 20, "PRIMARY INSURANCE CO. POLICY # GROUP #")
    c.drawString(53, y - 40, "TEST INSURANCE 0000000000 NJ00000")
    c.save()
    return buf.getvalue()


def doctor_pdf() -> bytes:
    """Same layout as a doctor's office 'Summary of Charges' statement (fake patient and provider)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    h = A4[1]

    def at(x, top, text):
        c.drawString(x, h - top - 9, text)

    at(241, 160, "Summary of Charges")
    for x, word in [(77, "Date"), (183, "Description"), (318, "Provider"), (388, "Charges"), (446, "Credits"),
                    (497, "Balance")]:
        at(x, 184, word)
    at(60, 205, "Charges for TEST,PATIENT in Sample Pediatrics")
    at(60, 226, "11/17/2025")
    at(134, 226, "Office/Outpatient Established")
    at(305, 226, "Sam Doctor,")
    at(395, 226, "420.00")
    at(508, 226, "10.00")
    at(134, 238, "Mod Mdm 30 Min")
    at(305, 238, "MD")
    at(60, 259, "12/02/2025")
    at(134, 259, "Insurance Payment - Test Plan")
    at(447, 259, "230.07")
    at(134, 271, "Horizon of Test")
    at(60, 292, "11/25/2025")
    at(134, 292, "Insurance Adjustment - Test Plan")
    at(447, 292, "179.93")
    at(134, 304, "Horizon of Test")
    at(134, 316, "CO-Pay Amount")
    c.save()
    return buf.getvalue()


def _read(data: bytes):
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    try:
        return read_real_bill(path)
    finally:
        os.remove(path)


# ---------- reader ----------

def test_hospital_summary_bill():
    r = _read(hospital_pdf())
    b = r.bill
    assert r.has_total and b.stated_subtotal == Decimal("36780.56") and len(b.lines) == 14
    assert [ln.description for ln in b.lines] == [d for d, _ in HOSPITAL_LINES]
    assert [ln.code for ln in b.lines] == ["0250", "0258", "0260", "0272", "0300", "0301", "0302", "0305",
                                           "0312", "0360", "0370", "0450", "0636", "0710"]
    assert all(ln.quantity == 1 and ln.unit_price == ln.line_total for ln in b.lines)
    assert run_checks(b).flag_count == 0                     # adds up, no repeats
    joined = " ".join(ln.description for ln in b.lines)
    assert "JANE" not in joined and "HAR-" not in joined and "Insurance" not in joined


def test_hospital_total_mismatch_is_flagged():
    r = _read(hospital_pdf(total="$36,880.56"))
    flags = run_checks(r.bill).flags
    assert [f.rule for f in flags] == ["subtotal_mismatch"] and flags[0].actual == Decimal("36880.56")


def test_doctor_statement():
    r = _read(doctor_pdf())
    b = r.bill
    assert not r.has_total and len(b.lines) == 1
    line = b.lines[0]
    assert line.description == "Office/Outpatient Established Mod Mdm 30 Min"   # wrapped line joined
    assert line.code == "99214" and line.line_total == Decimal("420.00")       # payments/adjustments skipped
    assert b.date_of_service.isoformat() == "2025-11-17"
    assert "TEST,PATIENT" not in line.description and "Doctor" not in line.description


def test_uncoded_duplicates_need_the_same_description():
    same_price = [("X-ray room fee", "$100.00"), ("Lab handling fee", "$100.00")]
    r = _read(hospital_pdf(total="$200.00", lines=same_price))
    assert [ln.code for ln in r.bill.lines] == ["", ""]
    assert run_checks(r.bill).flag_count == 0               # different charges, same price: not duplicates
    twice = [("X-ray room fee", "$100.00"), ("X-ray room fee", "$100.00")]
    r = _read(hospital_pdf(total="$200.00", lines=twice))
    flags = run_checks(r.bill).flags
    assert [f.rule for f in flags] == ["duplicate_line"] and 'same charge "X-ray room fee"' in flags[0].message


def test_coded_duplicates_unchanged():
    """The original rule for coded lines: same code + price + qty, wording ignored."""
    bill = Bill(bill_id="T", stated_subtotal=Decimal("236"), lines=[
        dict(line_no=1, code="80053", description="Comprehensive metabolic panel", quantity=1,
             unit_price=Decimal("118"), line_total=Decimal("118")),
        dict(line_no=2, code="80053", description="CMP lab panel", quantity=1,
             unit_price=Decimal("118"), line_total=Decimal("118"))])
    flags = run_checks(bill).flags
    assert [f.rule for f in flags] == ["duplicate_line"] and "same code 80053" in flags[0].message


def test_not_a_bill():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 700, "Hello, this is just a letter with no charges.")
    c.save()
    assert _read(buf.getvalue()) is None


@pytest.mark.parametrize("text,code", [
    ("Emergency Room - General Classification", "0450"), ("Clinical lab services", ""),
    ("Venipuncture blood draw", ""), ("Office/Outpatient New Low Mdm", "99203"), ("Something else", ""),
])
def test_code_matching(text, code):
    assert match_code(text) == code


# ---------- upload end to end ----------

@pytest.fixture(scope="module")
def c():
    with TestClient(server.app) as client:
        r = client.post("/api/auth/signup", json={"email": "real@example.com", "password": "s3cretpass1",
                                                  "accept_terms": True})
        client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        yield client


def test_upload_real_hospital_bill(c):
    r = c.post("/api/upload/pdf", files={"file": ("bill.pdf", hospital_pdf(), "application/pdf")})
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["bill_format"] == "summary" and "itemized bill" in out["notice"]
    assert out["bill"]["label"] == "Uploaded bill" and len(out["bill"]["lines"]) == 14
    assert out["flags"]["flag_count"] == 0
    assert "er_visit" in [q["id"] for q in out["questions"]]       # 0450 still triggers the ER question
    bid = out["bill"]["id"]
    letter = c.post("/api/letters", json={"bill_id": bid, "letter_type": "request"})
    assert letter.status_code == 200
    marked = c.post(f"/api/bills/{bid}/marked-up", files={"file": ("bill.pdf", hospital_pdf(), "application/pdf")})
    assert marked.status_code == 400                               # nothing flagged: nothing to mark up


def test_upload_real_bill_with_wrong_total_then_letter_and_markup(c):
    pdf = hospital_pdf(total="$36,880.56")
    out = c.post("/api/upload/pdf", files={"file": ("bill.pdf", pdf, "application/pdf")}).json()
    assert [f["rule"] for f in out["flags"]["flags"]] == ["subtotal_mismatch"]
    bid = out["bill"]["id"]
    letter = c.post("/api/letters", json={"bill_id": bid, "letter_type": "dispute"}).json()
    assert "$36,880.56" in letter["text"]
    marked = c.post(f"/api/bills/{bid}/marked-up", files={"file": ("bill.pdf", pdf, "application/pdf")})
    assert marked.status_code == 200 and marked.headers["x-marked-on-original"] == "false"


def test_upload_doctor_statement_and_edit_charges(c):
    out = c.post("/api/upload/pdf", files={"file": ("s.pdf", doctor_pdf(), "application/pdf")}).json()
    assert out["bill_format"] == "summary" and "added up the charges" in out["notice"]
    assert out["bill"]["date_of_service"] == "2025-11-17"
    # the charges step saves edited lines; a blank code must be accepted
    r = c.post("/api/bills", json={"label": "edited", "stated_subtotal": "420.00", "lines": [
        {"code": "", "description": "Office visit", "quantity": 1, "unit_price": "420.00", "line_total": "420.00"}]})
    assert r.status_code == 201, r.text


def test_demo_pdf_still_uses_the_original_reader(c):
    pdf = open("data/demo_bills.pdf", "rb").read()
    r = c.post("/api/upload/pdf", files={"file": ("d.pdf", pdf, "application/pdf")}, data={"account": "DEMO-002"})
    out = r.json()
    assert r.status_code == 201 and out["bill_format"] == "itemized" and out["notice"] is None
    assert out["bill"]["label"] == "DEMO-002" and [f["rule"] for f in out["flags"]["flags"]] == ["duplicate_line"]
    r = c.post("/api/upload/pdf", files={"file": ("d.pdf", pdf, "application/pdf")})
    assert r.status_code == 400 and "more than one bill" in r.json()["detail"]


def test_upload_unreadable_pdf(c):
    buf = io.BytesIO()
    cv = canvas.Canvas(buf)
    cv.drawString(72, 700, "Just a letter.")
    cv.save()
    r = c.post("/api/upload/pdf", files={"file": ("x.pdf", buf.getvalue(), "application/pdf")})
    assert r.status_code == 400 and "couldn't find any charges" in r.json()["detail"]
    
    
    

# ---------- MyChart-style "account details": department subtotal lines, then the items under them ----------

def mychart_pdf() -> bytes:
    rows = [
        ("Billed to Insurance", "$1,402.12"), ("Insurance covered", "-$1,000.00"), ("Copay", "$402.12"),
        ("Detailed Account Information", None),
        ("Pharmacy - General Classification", "$933.10"),
        ("Lactated Ringer's Parenteral Solution (0264-7750-00)", "$0.02"),
        ("Sugammadex 100 Mg/Ml Solution (0006-5423-12) - quantity: 2", "$933.08"),
        ("Laboratory - General Classification", "$287.00"),
        ("HC Glucose Blood Test With Device - 82962 (CPT®)", "$87.00"),
        ("HC Thromboplas Time Partial - Aptt - 85730 (CPT®)", "$140.00"),
        ("HC Venipuncture - 36415 (CPT®)", "$60.00"),
        ("Medical/Surgical Supplies and Devices - General Classification", "$182.02"),
        ("Trocar Laparoscopic 100mm 12mm Sterile Latex Free Optical", "$170.00"),
        ("Access System Abdominal", None),
        ("Metronidazole 500 Mg/100 Ml Piggyback (0409-0152-24) - quantity:", "$12.02"),
        ("50 - J1836 (HCPCS)", None),
        ("Payments and Adjustments", None), ("Test Plan", "-$1,000.00"),
    ]
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 740
    for desc, amount in rows:
        c.drawString(40, y, desc)
        if amount:
            c.drawRightString(570, y, amount)
        y -= 18
    c.save()
    return buf.getvalue()


def test_mychart_department_lines_are_not_double_counted():
    r = _read(mychart_pdf())
    b = r.bill
    assert r.has_total and b.stated_subtotal == Decimal("1402.12")
    assert sum(ln.line_total for ln in b.lines) == Decimal("1402.12")       # departments dropped, items kept
    assert not any("Classification" in ln.description for ln in b.lines)
    assert [ln.code for ln in b.lines] == ["", "", "82962", "85730", "36415", "", "J1836"]
    assert b.lines[5].description.endswith("Access System Abdominal")        # wrapped line joined
    assert b.lines[3].description == "HC Thromboplas Time Partial - Aptt"     # code removed from the text
    assert run_checks(b).flag_count == 0