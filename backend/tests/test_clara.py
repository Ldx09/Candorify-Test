"""Clara, the help assistant. Run: pytest -q tests/test_clara.py"""
import os
import tempfile

os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

import pytest
from fastapi.testclient import TestClient

import server
from app.api.routes import clara as route
from app.clara import faq as clara
from app.translation import gemini_client


@pytest.fixture()
def c(monkeypatch):
    route._recent.clear()
    with TestClient(server.app) as client:   # no login: Clara is public
        yield client


def no_ai(monkeypatch):
    def fail(*a, **k):
        raise gemini_client.GeminiUnavailable("off in tests")
    monkeypatch.setattr(gemini_client, "generate_json", fail)


def test_faq_file_is_valid():
    book = clara.load()
    assert len(book.faqs) >= 15 and len({f.id for f in book.faqs}) == len(book.faqs)
    assert book.chips and all(book.by_id(c) for c in book.chips)


def test_start(c):
    out = c.get("/api/clara/start").json()
    assert out["name"] == "Clara" and out["greeting"] and len(out["chips"]) >= 3


def test_chip_gives_its_answer(c):
    out = c.post("/api/clara/ask", json={"faq_id": "itemized"}).json()
    assert out["source"] == "faq" and out["faq_id"] == "itemized" and "itemized" in out["answer"]


@pytest.mark.parametrize("message,faq_id", [
    ("how do i get an itemized bill?", "itemized"), ("Is my data safe", "privacy"),
    ("can I upload a picture of my bill", "photo"), ("how much does it cost", "cost"),
    ("my hospital charged me twice", "what-checks"), ("whats a cpt code", "codes"),
])
def test_typed_questions_match_the_faq(c, monkeypatch, message, faq_id):
    no_ai(monkeypatch)
    out = c.post("/api/clara/ask", json={"message": message}).json()
    assert out["source"] == "faq" and out["faq_id"] == faq_id


def test_contact_question_opens_the_form(c):
    out = c.post("/api/clara/ask", json={"message": "I want to talk to a human"}).json()
    assert out["faq_id"] == "contact" and out["show_contact"] is True


def test_hello_and_thanks(c):
    assert "Hi" in c.post("/api/clara/ask", json={"message": "hey Clara!"}).json()["answer"]
    assert "welcome" in c.post("/api/clara/ask", json={"message": "thank you"}).json()["answer"]


def test_unknown_without_ai_offers_contact(c, monkeypatch):
    no_ai(monkeypatch)
    out = c.post("/api/clara/ask", json={"message": "what's the weather in Newark"}).json()
    assert out["source"] == "none" and out["show_contact"] is True


def test_ai_fallback_uses_faq_only_and_drops_unknown_ids(c, monkeypatch):
    seen = {}

    def fake(prompt, **k):
        seen["prompt"] = prompt
        return {"answer": "We look for double charges and wrong totals.", "related": ["what-checks", "made-up"]}
    monkeypatch.setattr(gemini_client, "generate_json", fake)
    out = c.post("/api/clara/ask", json={"message": "zzz something unusual about my visit"}).json()
    assert out["source"] == "ai" and [r["id"] for r in out["related"]] == ["what-checks"]
    assert "Answer ONLY with facts written in the FAQ" in seen["prompt"]


def test_ai_saying_no_answer_falls_back(c, monkeypatch):
    monkeypatch.setattr(gemini_client, "generate_json", lambda prompt, **k: {"answer": None, "related": []})
    out = c.post("/api/clara/ask", json={"message": "zzz something unusual"}).json()
    assert out["source"] == "none" and out["show_contact"]


def test_bad_input(c):
    assert c.post("/api/clara/ask", json={"message": "   "}).status_code == 422
    assert c.post("/api/clara/ask", json={"message": "x" * 501}).status_code == 422
    assert c.post("/api/clara/ask", json={"faq_id": "nope"}).status_code == 404


def test_rate_limit(c):
    for _ in range(route.RATE_LIMIT):
        assert c.post("/api/clara/ask", json={"faq_id": "cost"}).status_code == 200
    assert c.post("/api/clara/ask", json={"faq_id": "cost"}).status_code == 429