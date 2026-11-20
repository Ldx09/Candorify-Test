"""Who paid what: reading payments from bills, the payment checks, saving, letters. FAKE data only.
Run: pytest -q tests/test_payments.py"""
import os
import tempfile
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

import server
from app.core.schema_upgrade import add_missing_columns
from app.engine.checks import run_checks
from app.engine.payments import extract_payments
from app.models.bill import Bill
from app.models.payments import Payments
from tests.test_real_bills import doctor_pdf, hospital_pdf

D = Decimal


def bill_with(payments: Payments | None, total="1000.00", lines=None) -> Bill:
    lines = lines or [dict(line_no=1, code="99284", description="ER visit", quantity=1,
                           unit_price=D(total), line_total=D(total))]
    return Bill(bill_id="T", stated_subtotal=D(total), lines=lines, payments=payments)


# ---------- reading ----------

def test_mychart_style_summary():
    pages = [["Paid off", "$1,000.00", "-$900.00", "Billed to Insurance $1,000.00", "Insurance covered -$900.00",
              "Remaining responsibility $100.00", "Copay $100.00", "Detailed Account Information",
              "HC ER Level 5 - 99285 (CPT®) $1,000.00", "Payments and Adjustments", "Test Plan -$900.00",
              "Mychart Payment - Sep 26, 2026 -$100.00", "Need More Time to Pay?"]]
    p = extract_payments(pages, D("1000.00"))
    assert (p.insurance_paid, p.patient_responsibility, p.patient_paid, p.balance_due) == \
        (D("900.00"), D("100.00"), D("100.00"), D("0.00"))
    assert p.adjustments is None and p.other_payments is None   # the plan's line isn't counted twice


def test_statement_style_summary():
    pages = [["Total Charges: $36,780.56", "Adjustments: -$5,741.45", "Payments Received: -$30,489.11",
              "Total Amount Due: $550.00", "Pay as little as $69.00 / month for 8 months."],
             ["Total Hospital Charges $36,780.56", "Insurance Adjustments -$5,741.45",
              "Insurance Payments -$30,489.11", "Overall Patient Responsibility $550.00"]]
    p = extract_payments(pages, D("36780.56"))
    assert (p.insurance_paid, p.adjustments, p.patient_responsibility, p.balance_due) == \
        (D("30489.11"), D("5741.45"), D("550.00"), D("550.00"))
    assert p.other_payments is None and p.patient_paid is None


def test_doctor_statement_columns():
    pages = [["Date Description Provider Charges Credits Balance",
              "11/17/2025 Office/Outpatient Established Sam Doctor, MD 420.00 10.00",
              "12/02/2025 Insurance Payment - Test Plan 230.07",
              "11/25/2025 Insurance Adjustment - Test Plan 179.93", "CO-Pay Amount"]]
    p = extract_payments(pages, D("420.00"))
    assert (p.insurance_paid, p.adjustments, p.balance_due) == (D("230.07"), D("179.93"), D("10.00"))


def test_charges_only_bill_has_no_payments():
    assert extract_payments([["99284 Emergency visit 1 $1,450.00 $1,450.00", "Total charges $1,450.00"]],
                            D("1450.00")) is None


def test_payer_not_shown_and_credit_balance():
    p = extract_payments([["Payments received -$300.00", "Credit balance $25.00"]], D("500.00"))
    assert p.other_payments == D("300.00") and p.balance_due == D("-25.00")
    p = extract_payments([["Account balance 25.00 CR"]], D("500.00"))
    assert p.balance_due == D("-25.00")


def test_misread_amount_is_dropped_and_marked_uncertain():
    p = extract_payments([["Insurance Payments $900.00", "Insurance Adjustments -85,741.45", "Amount due $50.00"]],
                         D("1000.00"))
    assert p.adjustments is None and p.uncertain and p.insurance_paid == D("900.00")
    assert run_checks(bill_with(p)).flag_count == 0          # not enough to check: no false alarm


# ---------- checks ----------

def test_adds_up_no_flags():
    p = Payments(insurance_paid=D("700"), adjustments=D("200"), patient_paid=D("50"), balance_due=D("50"))
    assert run_checks(bill_with(p)).flag_count == 0


def test_payment_mismatch():
    p = Payments(insurance_paid=D("700"), adjustments=D("200"), balance_due=D("150"))
    flags = run_checks(bill_with(p)).flags
    assert [f.rule for f in flags] == ["payment_mismatch"]
    assert flags[0].expected == D("100") and flags[0].actual == D("150") and "$100.00" in flags[0].message


def test_payment_mismatch_from_share():
    p = Payments(patient_responsibility=D("100"), patient_paid=D("40"), balance_due=D("100"))
    flags = run_checks(bill_with(p)).flags
    assert [f.rule for f in flags] == ["payment_mismatch"] and flags[0].expected == D("60")


def test_overpaid_and_credit():
    p = Payments(insurance_paid=D("900"), patient_responsibility=D("100"), patient_paid=D("150"), balance_due=D("-50"))
    rules = [f.rule for f in run_checks(bill_with(p)).flags]
    assert rules == ["overpaid"]                              # 1000 - 900 - 150 = -50: adds up, but a refund is due
    flag = run_checks(bill_with(p)).flags[0]
    assert "refund of $50.00" in flag.message
    p = Payments(balance_due=D("-25"))
    assert "credit of $25.00" in run_checks(bill_with(p)).flags[0].message


def test_wrong_printed_total_is_not_flagged_twice():
    lines = [dict(line_no=1, code="A", description="x", quantity=1, unit_price=D("900"), line_total=D("900"))]
    p = Payments(insurance_paid=D("800"), balance_due=D("100"))
    rules = [f.rule for f in run_checks(bill_with(p, total="1000.00", lines=lines)).flags]
    assert rules == ["subtotal_mismatch"]


# ---------- end to end ----------

@pytest.fixture(scope="module")
def c():
    with TestClient(server.app) as client:
        r = client.post("/api/auth/signup", json={"email": "pay@example.com", "password": "s3cretpass1",
                                                  "accept_terms": True})
        client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        yield client


def test_upload_returns_payments(c):
    out = c.post("/api/upload/pdf", files={"file": ("b.pdf", hospital_pdf(), "application/pdf")}).json()
    p = out["bill"]["payments"]
    assert p["insurance_paid"] == "30489.11" and p["adjustments"] == "5741.45" and p["balance_due"] == "550.00"
    assert out["flags"]["flag_count"] == 0
    bid = out["bill"]["id"]
    assert c.get(f"/api/bills/{bid}").json()["payments"]["patient_responsibility"] == "550.00"   # saved


def test_doctor_statement_payments(c):
    out = c.post("/api/upload/pdf", files={"file": ("s.pdf", doctor_pdf(), "application/pdf")}).json()
    p = out["bill"]["payments"]
    assert p["insurance_paid"] == "230.07" and p["adjustments"] == "179.93" and p["balance_due"] == "10.00"
    assert out["flags"]["flag_count"] == 0


def test_demo_bill_has_no_payments(c):
    pdf = open("data/demo_bills.pdf", "rb").read()
    out = c.post("/api/upload/pdf", files={"file": ("d.pdf", pdf, "application/pdf")}, data={"account": "DEMO-002"}).json()
    assert out["bill"]["payments"] is None


def test_edited_payments_are_checked_and_go_in_the_letter(c):
    body = {"label": "edited", "stated_subtotal": "1000.00",
            "lines": [{"code": "99284", "description": "ER visit", "quantity": 1, "unit_price": "1000.00",
                       "line_total": "1000.00"}],
            "payments": {"insurance_paid": "700.00", "adjustments": "200.00", "patient_paid": "100.00",
                         "patient_responsibility": "60.00", "balance_due": "50.00"}}
    bill = c.post("/api/bills", json=body).json()
    assert bill["payments"]["insurance_paid"] == "700.00"
    review = c.post("/api/upload/review", json={"bill_id": bill["id"], "answers": []}).json()
    rules = sorted(f["rule"] for f in review["flags"]["flags"])
    assert rules == ["overpaid", "payment_mismatch"]
    letter = c.post("/api/letters", json={"bill_id": bill["id"], "letter_type": "dispute"}).json()["text"]
    assert "do not add up" in letter and "I paid $100.00, but my share was $60.00" in letter
    marked = c.post(f"/api/bills/{bill['id']}/marked-up")
    assert marked.status_code == 200
    bad = dict(body, payments={"insurance_paid": "-5"})
    assert c.post("/api/bills", json=bad).status_code == 422


def test_old_database_gets_the_new_column(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE bills (id INTEGER PRIMARY KEY, label VARCHAR(100))"))
        conn.execute(text("INSERT INTO bills (label) VALUES ('kept')"))
    add_missing_columns(eng)
    add_missing_columns(eng)   # safe to run twice
    assert "payments" in {c["name"] for c in inspect(eng).get_columns("bills")}
    with eng.connect() as conn:
        assert conn.execute(text("SELECT label FROM bills")).scalar() == "kept"