"""End-to-end: upload -> questions -> review -> answer flags -> letter. Run: pytest -q tests/test_questions_flow.py"""
import json
import os
import tempfile

os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

import pytest
from fastapi.testclient import TestClient

import server
from app.core.database import SessionLocal
from app.models.answer_record import AnswerRecord
from app.questions import localize
from app.translation import gemini_client


@pytest.fixture(scope="module")
def c():
    with TestClient(server.app) as client:
        r = client.post("/api/auth/signup", json={"email": "q@example.com", "password": "s3cretpass1",
                                                  "accept_terms": True})
        token = r.json().get("access_token") or client.post(
            "/api/auth/login", json={"email": "q@example.com", "password": "s3cretpass1"}).json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


def sample(c, sid, **extra):
    r = c.post("/api/upload/sample", json={"sample_id": sid, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def review(c, bill_id, answers):
    return c.post("/api/upload/review", json={"bill_id": bill_id, "answers": [
        {"question_id": k, "value": v} for k, v in answers.items()]})


def test_demo_001_room_nights(c):
    out = sample(c, "DEMO-001")
    assert out["bill"]["date_of_service"] == "2026-09-01"
    assert out["flags"]["flag_count"] == 0
    ids = [q["id"] for q in out["questions"]]
    assert ids == ["room_nights", "er_visit", "imaging:71046", "medicine_given:J2405", "supplies_received:A6402"]
    er = out["questions"][1]
    assert "09/01/2026" in er["text"] and er["choices"][0] == {"value": "Yes", "label": "Yes"}
    r = review(c, out["bill"]["id"], {"room_nights": 3, "er_visit": "Yes", "imaging:71046": "Not sure"})
    assert r.status_code == 200, r.text
    flags = r.json()["flags"]["flags"]
    assert len(flags) == 1 and flags[0]["rule"] == "answer_mismatch" and flags[0]["question_id"] == "room_nights"
    assert flags[0]["message"] == "You said 3 nights, but the bill charges 4 room days."
    assert flags[0]["status"] == "investigating" and r.json()["new_flag_ids"] == [flags[0]["id"]]


def test_demo_002_engine_and_answer_flags(c):
    out = sample(c, "DEMO-002")
    assert [f["rule"] for f in out["flags"]["flags"]] == ["duplicate_line"]
    bid = out["bill"]["id"]
    r = review(c, bid, {"ambulance_miles": 10, "blood_draws": "seems like too many"}).json()
    rules = sorted((f["rule"], f.get("question_id")) for f in r["flags"]["flags"])
    assert rules == [("answer_mismatch", "ambulance_miles"), ("answer_mismatch", "blood_draws"),
                     ("duplicate_line", None)]
    # 20 of 25 miles is exactly 80% -> no flag; status of a still-matching flag is kept
    draws = next(f for f in r["flags"]["flags"] if f.get("question_id") == "blood_draws")
    assert c.patch(f"/api/bills/flags/{draws['id']}", json={"status": "add_to_letter"}).status_code == 200
    r = review(c, bid, {"ambulance_miles": 20, "blood_draws": "Seems like too many"}).json()
    qs = {f.get("question_id"): f for f in r["flags"]["flags"] if f["rule"] == "answer_mismatch"}
    assert set(qs) == {"blood_draws"} and qs["blood_draws"]["status"] == "add_to_letter"
    assert qs["blood_draws"]["id"] == draws["id"] and r["new_flag_ids"] == []
    # re-check keeps answer flags
    chk = c.post(f"/api/bills/{bid}/check").json()
    assert {f["rule"] for f in chk["flags"]} == {"duplicate_line", "answer_mismatch"}
    # letter uses the letter_text
    letter = c.post("/api/letters", json={"bill_id": bid, "letter_type": "dispute"}).json()
    assert "Charge does not match the care I received" in letter["text"]
    assert draws["id"] in letter["flag_ids"] and len(letter["flag_ids"]) == 1
    # saved answers come back with the questions
    q = c.get(f"/api/bills/{bid}/questions").json()
    assert q["answers"] == {"ambulance_miles": "20", "blood_draws": "Seems like too many"}


def test_demo_003_and_004(c):
    out = sample(c, "DEMO-003")
    assert [f["rule"] for f in out["flags"]["flags"]] == ["line_math"]
    assert "comfort_items" not in [q["type"] for q in out["questions"]]
    r = review(c, out["bill"]["id"], {"private_room": "No", "therapy_time:97110": "Shorter than that"}).json()
    assert sorted(f.get("question_id") or "" for f in r["flags"]["flags"]) == ["", "private_room", "therapy_time:97110"]
    out = sample(c, "DEMO-004")
    r = review(c, out["bill"]["id"], {"blood_transfusion": "No", "observation": "Yes"}).json()
    assert [f["question_id"] for f in r["flags"]["flags"]] == ["blood_transfusion"]


def test_bad_answers(c):
    bid = sample(c, "DEMO-001")["bill"]["id"]
    assert review(c, bid, {"room_nights": "three"}).status_code == 422
    assert review(c, bid, {"er_visit": "Maybe"}).status_code == 422
    assert review(c, bid, {"icu_nights": 1}).status_code == 422          # not a question for this bill
    assert review(c, bid, {"room_nights": None, "er_visit": ""}).json()["flags"]["flag_count"] == 0
    assert review(c, 999999, {}).status_code == 404


def test_pdf_upload(c):
    pdf = open("data/demo_bills.pdf", "rb").read()
    r = c.post("/api/upload/pdf", files={"file": ("bill.pdf", pdf, "application/pdf")})
    assert r.status_code == 400 and "DEMO-001" in r.json()["detail"]
    r = c.post("/api/upload/pdf", files={"file": ("bill.pdf", pdf, "application/pdf")}, data={"account": "demo-003"})
    assert r.status_code == 201, r.text
    assert r.json()["bill"]["date_of_service"] == "2026-09-05" and len(r.json()["questions"]) == 5
    assert c.post("/api/upload/pdf", files={"file": ("x.pdf", b"hello", "application/pdf")}).status_code == 400
    assert c.post("/api/upload/pdf", files={"file": ("x.pdf", b"%PDF" + b"0" * (5 * 1024 * 1024),
                                                     "application/pdf")}).status_code == 413
    assert c.post("/api/upload/pdf", files={"file": ("bill.pdf", pdf, "application/pdf")},
                  data={"account": "NOPE"}).status_code == 400


def test_delete_removes_answers(c):
    bid = sample(c, "DEMO-001")["bill"]["id"]
    review(c, bid, {"room_nights": 2})
    assert c.delete(f"/api/bills/{bid}").status_code == 204
    with SessionLocal() as db:
        assert db.query(AnswerRecord).filter_by(bill_id=bid).count() == 0


def test_other_users_bill(c):
    bid = sample(c, "DEMO-001")["bill"]["id"]
    other = TestClient(server.app)
    tok = other.post("/api/auth/signup", json={"email": "z@example.com", "password": "s3cretpass1",
                                                "accept_terms": True}).json()["access_token"]
    other.headers["Authorization"] = f"Bearer {tok}"
    assert other.post("/api/upload/review", json={"bill_id": bid, "answers": []}).status_code == 404
    assert other.get(f"/api/bills/{bid}/questions").status_code == 404


# ---------- translation of questions (Gemini mocked) ----------

def _fake(reply_fn):
    def fake(prompt, client=None, timeout=None, retries=1, temperature=0):
        assert timeout == 5.0 and retries == 0
        data = json.loads(prompt[prompt.rindex('{"questions"'):])
        return reply_fn(data["questions"])
    return fake


def test_gemini_questions(c, monkeypatch):
    localize.clear_cache()
    def good(qs):
        return {"questions": [{"id": q["id"], "text": "ES " + q["text"],
                               **({"choices": ["ES " + x for x in q["choices"]]} if "choices" in q else {})} for q in qs]}
    monkeypatch.setattr(gemini_client, "generate_json", _fake(good))
    out = sample(c, "DEMO-001", language="es")
    assert out["language"] == "es" and all(q["translated"] for q in out["questions"])
    er = out["questions"][1]
    assert er["text"].startswith("ES ") and er["choices"][1] == {"value": "No", "label": "ES No"}


def test_gemini_rejects_bad_numbers_and_order(c, monkeypatch):
    localize.clear_cache()
    def bad(qs):  # changes a number in the first question, adds one to the second, too long third
        out = [{"id": q["id"], "text": q["text"], **({"choices": q["choices"]} if "choices" in q else {})} for q in qs]
        out[0]["text"] = out[0]["text"].replace("4", "5")
        out[1]["text"] += " 7"
        out[2]["text"] = out[2]["text"] * 3
        return {"questions": out}
    monkeypatch.setattr(gemini_client, "generate_json", _fake(bad))
    out = sample(c, "DEMO-001", language="fr")
    assert [q["translated"] for q in out["questions"]] == [False, False, False, True, True]
    assert "4" in out["questions"][0]["text"]
    localize.clear_cache()
    monkeypatch.setattr(gemini_client, "generate_json", _fake(lambda qs: {"questions": list(reversed(qs))}))
    out = sample(c, "DEMO-001", language="de")
    assert not any(q["translated"] for q in out["questions"])
    assert "English" in out["translation_note"]


def test_saved_translation_fallback(c, monkeypatch, tmp_path):
    localize.clear_cache()
    def down(*a, **k):
        raise gemini_client.GeminiUnavailable("no key")
    monkeypatch.setattr(gemini_client, "generate_json", down)
    f = tmp_path / "t.json"
    f.write_text(json.dumps({"languages": {"es": {
        "types": {"room_nights": {"text": {"source": "x", "text": "¿Cuántas noches? La factura cobra {qty} días."}},
                  "er_visit": {"text": {"source": "x", "text": "¿Fue a urgencias el {date}?"}}},
        "choices": {"Yes": {"source": "Yes", "text": "Sí"}}}}}), encoding="utf-8")
    monkeypatch.setattr(localize, "TRANSLATIONS_FILE", f)
    out = sample(c, "DEMO-001", language="es")
    qs = out["questions"]
    assert qs[0]["text"] == "¿Cuántas noches? La factura cobra 4 días." and qs[0]["translated"]
    assert qs[1]["text"] == "¿Fue a urgencias el 09/01/2026?"
    assert qs[1]["choices"][0] == {"value": "Yes", "label": "Sí"} and qs[1]["choices"][1]["label"] == "No"
    assert not qs[2]["translated"]
    # answering with the English value still works
    r = review(c, out["bill"]["id"], {"er_visit": "No"}).json()
    assert r["flags"]["flags"][0]["question_id"] == "er_visit"
    localize.clear_cache()


def test_english_never_calls_gemini(c, monkeypatch):
    monkeypatch.setattr(gemini_client, "generate_json", lambda *a, **k: pytest.fail("called Gemini"))
    out = sample(c, "DEMO-002", language="en")
    assert out["translation_note"] is None


def test_translate_question_bank_script(monkeypatch, tmp_path):
    from scripts import translate_question_bank as tqb
    calls = []
    def fake(prompt, client=None, **k):
        data = json.loads(prompt[prompt.index("{\n"):])
        calls.append(len(data))
        out = {key: "T " + v for key, v in data.items()}
        out["types.room_nights.text"] = out["types.room_nights.text"].replace("{qty}", "{cantidad}")  # broken
        return {"translations": out}
    monkeypatch.setattr(gemini_client, "generate_json", fake)
    monkeypatch.setattr(tqb, "OUT", tmp_path / "out.json")
    summary = tqb.run(only=["es", "ar"])
    assert set(summary) == {"es", "ar"} and "rest stay English" in summary["es"]
    data = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))["languages"]["es"]
    assert "text" not in data["types"]["room_nights"]
    assert data["choices"]["Yes"]["text"] == "T Yes"
    first = calls[0]
    calls.clear()
    tqb.run(only=["es"])               # only the rejected one is sent again
    assert calls == [1] and first > 30
    assert len(tqb.english_items()) == first
    
    

# ---------- marked-up PDF ----------

def _pdf_text(data):
    import io
    import pdfplumber
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return len(pdf.pages), "\n".join(p.extract_text() or "" for p in pdf.pages)


def test_marked_up_on_original(c):
    pdf = open("data/demo_bills.pdf", "rb").read()
    up = c.post("/api/upload/pdf", files={"file": ("b.pdf", pdf, "application/pdf")}, data={"account": "DEMO-003"}).json()
    bid = up["bill"]["id"]
    review(c, bid, {"private_room": "No"})
    r = c.post(f"/api/bills/{bid}/marked-up", files={"file": ("b.pdf", pdf, "application/pdf")})
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["x-marked-on-original"] == "true" and r.headers["cache-control"] == "no-store"
    pages, text = _pdf_text(r.content)
    assert pages == 4 + 4 + 1                                 # original (4) + marked up (4) + summary page
    assert "Things to ask about" in text and "Line total doesn't match" in text and "private room" in text
    assert "original bill (unchanged)" in text
    
def test_marked_up_rebuilt_without_pdf_and_skips_dismissed(c):
    out = sample(c, "DEMO-002")
    bid = out["bill"]["id"]
    r = review(c, bid, {"ambulance_miles": 10}).json()
    miles = next(f for f in r["flags"]["flags"] if f.get("question_id") == "ambulance_miles")
    c.patch(f"/api/bills/flags/{miles['id']}", json={"status": "dismissed"})
    r = c.post(f"/api/bills/{bid}/marked-up")
    assert r.status_code == 200 and r.headers["x-marked-on-original"] == "false"
    _, text = _pdf_text(r.content)
    assert "reprinted by Candorify" in text and "duplicate" in text and "miles" not in text


def test_marked_up_wrong_pdf_falls_back_and_errors(c):
    pdf = open("data/demo_bills.pdf", "rb").read()
    bid = sample(c, "DEMO-002")["bill"]["id"]
    # PDF given, but the stored bill is DEMO-002 under label DEMO-002 -> rows match on the original
    r = c.post(f"/api/bills/{bid}/marked-up", files={"file": ("b.pdf", pdf, "application/pdf")})
    assert r.headers["x-marked-on-original"] == "true"
    # a bill with no flags
    clean = sample(c, "DEMO-001")["bill"]["id"]
    assert c.post(f"/api/bills/{clean}/marked-up").status_code == 400
    # not a PDF
    assert c.post(f"/api/bills/{bid}/marked-up", files={"file": ("x.pdf", b"hello", "application/pdf")}).status_code == 400
    # edited charges: the original no longer matches -> rebuilt
    gen = c.post("/api/upload/sample", json={"defect": "duplicate"}).json()["bill"]["id"]
    r = c.post(f"/api/bills/{gen}/marked-up", files={"file": ("b.pdf", pdf, "application/pdf")})
    assert r.status_code == 200 and r.headers["x-marked-on-original"] == "false"
    pages, text = _pdf_text(r.content)
    assert pages >= 4 + 2 and "reprint" in text              # their 4 original pages still come first