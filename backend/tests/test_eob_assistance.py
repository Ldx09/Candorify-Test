"""Insurance EOB comparison and the financial assistance checker. FAKE data only.
Run: pytest -q tests/test_eob_assistance.py"""
import io
import os
import tempfile
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import server
from app.engine import assistance
from app.engine.checks import run_checks
from app.engine.eob import read_eob_lines
from app.models.bill import Bill
from app.models.eob import EobSummary
from app.models.payments import Payments
from tests.test_real_bills import doctor_pdf, hospital_pdf

D = Decimal


def eob_pdf(rows: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 740
    for row in ["Test Health Plan", "EXPLANATION OF BENEFITS - THIS IS NOT A BILL", "Member: JANE TEST ID: TST0001",
                "Statement date: 03/02/2026"] + rows:
        c.drawString(40, y, row)
        y -= 18
    c.save()
    return buf.getvalue()


KV_EOB = ["Claim for services at Sample Hospital", "Amount billed $36,780.56", "Member rate $30,609.11",
          "Your plan paid $30,489.11", "Deductible $100.00", "Coinsurance $20.00", "What you owe $120.00"]


# ---------- reading ----------

def test_reads_key_value_eob():
    e = read_eob_lines([["Date of service: 01/15/2026"] + KV_EOB])
    assert (e.billed, e.allowed, e.plan_paid, e.you_owe) == (D("36780.56"), D("30609.11"), D("30489.11"), D("120.00"))
    assert [d.isoformat() for d in e.service_dates] == ["2026-01-15"]


def test_reads_table_eob_with_total_row():
    page = ["Statement date 02/20/2026",
            "Service Date Description Amount Billed Allowed Amount Plan Paid Deductible Copay Coinsurance What You Owe",
            "01/15/2026 Emergency room $5,249.00 $1,800.00 $1,400.00 $250.00 $0.00 $150.00 $400.00",
            "01/15/2026 Laboratory $864.00 $300.00 $300.00 $0.00 $0.00 $0.00 $0.00",
            "Total $6,113.00 $2,100.00 $1,700.00 $250.00 $0.00 $150.00 $400.00"]
    e = read_eob_lines([page])
    assert (e.billed, e.allowed, e.plan_paid, e.you_owe) == (D("6113.00"), D("2100.00"), D("1700.00"), D("400.00"))
    assert [d.isoformat() for d in e.service_dates] == ["2026-01-15"]


def test_you_owe_from_parts_and_not_an_eob():
    e = read_eob_lines([["Service Date Amount Billed Allowed Plan Paid Deductible Copay Coinsurance",
                         "11/17/2025 $420.00 $240.07 $230.07 $0.00 $10.00 $0.00"]])
    assert e.you_owe == D("10.00") and e.plan_paid == D("230.07")
    assert read_eob_lines([["Hello", "Total charges $100.00"]]) is None


# ---------- checks ----------

def bill(eob, payments=None, total="1000.00", dos=None) -> Bill:
    return Bill(bill_id="T", stated_subtotal=D(total), date_of_service=dos, payments=payments, eob=eob,
                lines=[dict(line_no=1, code="99284", description="ER", quantity=1, unit_price=D(total),
                            line_total=D(total))])


def test_bill_asks_more_than_eob():
    b = bill(EobSummary(you_owe=D("120"), plan_paid=D("880"), billed=D("1000")),
             Payments(insurance_paid=D("880"), patient_responsibility=D("550"), balance_due=D("550")))
    flags = run_checks(b).flags
    assert "eob_owe_mismatch" in [f.rule for f in flags]
    owe = next(f for f in flags if f.rule == "eob_owe_mismatch")
    assert owe.expected == D("120") and owe.actual == D("550") and "$430.00 more" in owe.message


def test_matching_eob_no_flags_and_other_visit_skipped():
    p = Payments(insurance_paid=D("880"), patient_responsibility=D("120"), balance_due=D("120"))
    assert run_checks(bill(EobSummary(you_owe=D("120"), plan_paid=D("880"), billed=D("1000")), p)).flag_count == 0
    from datetime import date
    other = EobSummary(you_owe=D("5"), plan_paid=D("1"), billed=D("50"), service_dates=[date(2026, 2, 1)])
    assert run_checks(bill(other, p, dos=date(2026, 1, 15))).flag_count == 0


def test_paid_and_billed_mismatch():
    p = Payments(insurance_paid=D("700"), balance_due=D("100"), adjustments=D("200"))
    rules = {f.rule for f in run_checks(bill(EobSummary(plan_paid=D("880"), billed=D("1200")), p)).flags}
    assert {"eob_paid_mismatch", "eob_billed_mismatch"} <= rules


# ---------- end to end ----------

@pytest.fixture(scope="module")
def c():
    with TestClient(server.app) as client:
        r = client.post("/api/auth/signup", json={"email": "eob@example.com", "password": "s3cretpass1",
                                                  "accept_terms": True})
        client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        yield client


def upload(c, pdf):
    return c.post("/api/upload/pdf", files={"file": ("b.pdf", pdf, "application/pdf")}).json()["bill"]["id"]


def test_eob_upload_flags_letter_and_remove(c):
    bid = upload(c, hospital_pdf())
    r = c.post(f"/api/bills/{bid}/eob", files={"file": ("eob.pdf", eob_pdf(KV_EOB), "application/pdf")})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["eob"]["you_owe"] == "120.00" and out["same_visit"] is None
    assert [f["rule"] for f in out["flags"]["flags"]] == ["eob_owe_mismatch"]
    assert c.get(f"/api/bills/{bid}").json()["eob"]["plan_paid"] == "30489.11"          # saved on the bill
    text = c.post("/api/letters", json={"bill_id": bid, "letter_type": "dispute"}).json()["text"]
    assert "my responsibility for this visit is $120.00" in text
    gone = c.delete(f"/api/bills/{bid}/eob").json()
    assert gone["eob"] is None and gone["flags"]["flag_count"] == 0


def test_eob_for_another_visit_is_not_compared(c):
    bid = upload(c, doctor_pdf())     # date of service 11/17/2025
    rows = ["Date of service: 12/01/2025", "Amount billed $95.00", "Plan paid $50.00", "What you owe $5.00"]
    out = c.post(f"/api/bills/{bid}/eob", files={"file": ("e.pdf", eob_pdf(rows), "application/pdf")}).json()
    assert out["same_visit"] is False and "don't match" in out["note"] and out["flags"]["flag_count"] == 0


def test_eob_photo_text_and_errors(c):
    bid = upload(c, hospital_pdf())
    out = c.post(f"/api/bills/{bid}/eob-text", json={"pages": [KV_EOB]}).json()
    assert out["eob"]["you_owe"] == "120.00"
    bad = c.post(f"/api/bills/{bid}/eob-text", json={"pages": [["Just a letter"]]})
    assert bad.status_code == 400 and "Explanation of Benefits" in bad.json()["detail"]
    assert c.post(f"/api/bills/{bid}/eob", files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 400
    assert c.post("/api/bills/999999/eob-text", json={"pages": [KV_EOB]}).status_code == 404


def test_edited_bill_keeps_its_eob(c):
    body = {"label": "edited", "stated_subtotal": "1000.00",
            "lines": [{"code": "99284", "description": "ER", "quantity": 1, "unit_price": "1000.00", "line_total": "1000.00"}],
            "payments": {"patient_responsibility": "300.00"}, "eob": {"you_owe": "100.00", "plan_paid": "700.00"}}
    b = c.post("/api/bills", json=body).json()
    assert b["eob"]["you_owe"] == "100.00"
    rules = [f["rule"] for f in c.post("/api/upload/review", json={"bill_id": b["id"], "answers": []}).json()["flags"]["flags"]]
    assert "eob_owe_mismatch" in rules


# ---------- financial assistance ----------

def test_poverty_lines():
    assert assistance.poverty_line(1, "NJ") == 15960 and assistance.poverty_line(4, None) == 33000
    assert assistance.poverty_line(1, "AK") == 19950 and assistance.poverty_line(2, "HI") == 24890


@pytest.mark.parametrize("size,income,state,insured,tier,program,phrase", [
    (3, 42000, "NJ", None, "free", "New Jersey Charity Care", "free hospital care"),
    (3, 60000, "NJ", True, "discount", "New Jersey Charity Care", "only 20%"),
    (3, 90000, "NJ", None, "discount", "New Jersey Charity Care", "discount"),   # above NJ's 300%: hospital policy
    (1, 25000, "TX", None, "free", None, "free or nearly free"),
    (1, 15000, "IN", None, "free", None, "Medicaid"),
    (1, 90000, None, None, "ask", None, "still lower"),
    (2, 40000, "WA", None, "free", "Washington Charity Care Act", "free hospital care"),
    (4, 120000, "OR", True, "discount", "Oregon hospital financial assistance (nonprofit hospitals)", "only 75%"),
])
def test_assistance_tiers(size, income, state, insured, tier, program, phrase):
    out = assistance.check(size, D(income), state, insured=insured, amount=D("550"))
    assert out["tier"] == tier and phrase in out["headline"]
    assert (out["state_program"] or {}).get("name") == program
    assert out["next_steps"] and out["rights"] and out["deadline"] and out["savings"]["text"]


def test_assistance_dollars_plan_and_letters():
    nj = assistance.check(3, D(60000), "NJ", amount=D("550"), hospital="Sample Hospital", date_of_service="09/12/2026")
    assert nj["savings"]["may_pay"] == D("110.00") and "save $440.00" in nj["savings"]["text"]
    assert "Dear Sample Hospital Billing Office" in nj["letter"] and "09/12/2026" in nj["letter"]
    assert "New Jersey Charity Care" in nj["letter"] and "$550.00" in nj["letter"]
    co = assistance.check(1, D(30000), "CO", insured=False, amount=D("3000"))
    assert co["payment_plan"]["legal_cap"] and co["payment_plan"]["monthly"] == D("100")
    rich = assistance.check(1, D(100000), "IN", insured=True, amount=D("5000"))
    assert rich["letter_subject"] == "Request for a discount and payment plan" and "$417.00 per month" in rich["letter"]
    assert not rich["payment_plan"]["legal_cap"] and rich["medicaid"] is None
    low = assistance.check(1, D(15000), "IN", amount=D("550"))
    assert low["medicaid"]["likely"] and "Medicaid" in low["letter"] and low["savings"]["may_pay"] == 0
    il = assistance.check(1, D(30000), "IL", insured=True)
    assert il["state_program"]["applies"] is False and il["savings"] is None


def test_every_state_works():
    for st in sorted(assistance.US_STATES):
        for income in (10000, 30000, 60000, 200000):
            out = assistance.check(2, D(income), st, amount=D("1000"))
            assert out["headline"] and out["letter"] and out["tier"] in ("free", "discount", "ask")


def test_assistance_endpoint_is_public_and_validates():
    with TestClient(server.app) as anon:
        r = anon.post("/api/assistance/check", json={"household_size": 2, "yearly_income": 30000, "state": "nj",
                                                     "amount": 550, "insured": True})
        assert r.status_code == 200 and r.json()["percent_of_poverty"] == 139
        assert "New Jersey Charity Care" in r.json()["letter"] and r.json()["savings"]["may_pay"] == "0.00"
        assert anon.post("/api/assistance/check", json={"household_size": 0, "yearly_income": 1}).status_code == 422
        assert anon.post("/api/assistance/check", json={"household_size": 2, "yearly_income": 1, "state": "ZZ"}).status_code == 422
        assert anon.post("/api/assistance/check", json={"household_size": 1, "yearly_income": 1}).status_code == 200