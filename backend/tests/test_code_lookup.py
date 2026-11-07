"""Code lookup: CPT, HCPCS and ICD-10-CM, with NLM up (mocked) and down. Run: pytest -q tests/test_code_lookup.py"""
import httpx
import pytest

from app.translation import nlm_client as nlm
from app.translation import service
from app.translation.fallback import FALLBACK_CODES
from app.translation.service import classify, lookup_code


@pytest.fixture(autouse=True)
def fresh():
    service.clear_cache()
    yield
    service.clear_cache()


def nlm_down(monkeypatch):
    def boom(*a, **k):
        raise nlm.ProviderUnavailable("offline")
    monkeypatch.setattr(nlm, "search", boom)


def test_every_backup_code_has_the_right_shape():
    for code, (system, _, _) in FALLBACK_CODES.items():
        assert classify(code) == system, f"{code} looks like {classify(code)}, listed as {system}"


@pytest.mark.parametrize("picked", [None, "CPT", "HCPCS", "ICD-10-CM"])
def test_every_backup_code_resolves_offline_whatever_type_is_picked(monkeypatch, picked):
    nlm_down(monkeypatch)
    for code, (system, desc, plain) in FALLBACK_CODES.items():
        info = lookup_code(code, system=picked)
        assert info.source == "fallback", (code, picked)
        assert info.system == system and info.plain_english == plain


def test_icd_without_dot_and_lowercase(monkeypatch):
    nlm_down(monkeypatch)
    for typed in ("r109", "R109", " r10.9 "):
        info = lookup_code(typed, system="ICD-10-CM")
        assert info.code == "R10.9" and info.plain_english == "Belly pain"
    assert lookup_code("u071").system == "ICD-10-CM"


def test_wrong_type_picked_uses_the_codes_real_type(monkeypatch):
    nlm_down(monkeypatch)
    assert lookup_code("J2405", system="CPT").system == "HCPCS"
    assert lookup_code("R07.9", system="CPT").system == "ICD-10-CM"
    assert lookup_code("99284", system="HCPCS").system == "CPT"


def test_nlm_answer_uses_official_text_and_our_plain_english(monkeypatch):
    calls = []

    def fake(system, code, client=None):
        calls.append((system, code))
        if system == "HCPCS":
            return [{"code": "J1885", "long_desc": "Injection, ketorolac tromethamine, per 15 mg"},
                    {"code": "J9999", "long_desc": "Not this one"}]
        return [{"code": "S93.401A", "name": "Sprain of unspecified ligament of right ankle, initial encounter"}]

    monkeypatch.setattr(nlm, "search", fake)
    h = lookup_code("j1885", system="HCPCS")
    assert h.source == "nlm" and h.description.startswith("Injection, ketorolac") and "Toradol" in h.plain_english
    i = lookup_code("S93401A", system="ICD-10-CM")
    assert i.source == "nlm" and i.code == "S93.401A" and i.plain_english == "Sprained right ankle, first visit"
    assert calls[-1] == ("ICD-10-CM", "S93.401A")


def test_codes_not_in_backup_come_from_nlm(monkeypatch):
    monkeypatch.setattr(nlm, "search", lambda s, c, client=None: [{"code": "E78.5", "name": "Hyperlipidemia, unspecified"}])
    info = lookup_code("E78.5", system="ICD-10-CM")
    assert info.source == "nlm" and info.plain_english == "Hyperlipidemia, unspecified"


def test_unknown_code_is_not_found(monkeypatch):
    monkeypatch.setattr(nlm, "search", lambda s, c, client=None: [])
    assert lookup_code("Z99.999", system="ICD-10-CM").source == "not_found"
    assert lookup_code("12345", system="CPT").source == "not_found"


def test_nlm_request_shape():
    """The exact NLM URL/params the app sends, checked against a fake transport."""
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json=[1, ["R10.9"], None, [["R10.9", "Unspecified abdominal pain"]]])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rows = nlm.search("ICD-10-CM", "R10.9", client=client)
    assert rows == [{"code": "R10.9", "name": "Unspecified abdominal pain"}]
    assert "icd10cm/v3/search" in seen["url"] and "sf=code" in seen["url"]
    
    

# ---------- not-found messages and the missing-codes log ----------

def test_not_found_messages(monkeypatch):
    monkeypatch.setattr(nlm, "search", lambda s, c, client=None: [])
    cpt = lookup_code("99999")
    assert cpt.source == "not_found" and "American Medical Association" in cpt.message
    assert "diagnosis code" in lookup_code("Z99.999").message
    assert "HCPCS" in lookup_code("J9998").message
    assert "doesn't look like a billing code" in lookup_code("hello").message
    assert lookup_code("99284").message is None          # found codes carry no message


def test_offline_message_when_nlm_is_down(monkeypatch):
    nlm_down(monkeypatch)
    info = lookup_code("E78.5")
    assert info.source == "not_found" and info.message == service.OFFLINE_MESSAGE


def test_large_cpt_list_loaded():
    cpt = [c for c, (s, _, _) in FALLBACK_CODES.items() if s == "CPT"]
    assert len(cpt) >= 500
    assert lookup_code("71045").plain_english == "Chest X-ray with one picture"


def test_translate_route_logs_missing_codes(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.api.routes import translate
    from app.core.database import Base, get_db
    from app.models.missing_code_record import MissingCodeRecord
    from app.services.missing_codes import most_asked

    engine = create_engine(f"sqlite:///{tmp_path}/m.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[MissingCodeRecord.__table__])
    Session = sessionmaker(bind=engine)

    def db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app = FastAPI()
    app.include_router(translate.router, prefix="/api")
    app.dependency_overrides[get_db] = db
    c = TestClient(app)
    monkeypatch.setattr(nlm, "search", lambda s, code, client=None: [])

    for _ in range(3):
        r = c.get("/api/translate", params={"code": "99999"}).json()
    assert r["source"] == "not_found" and "American Medical Association" in r["message"]
    c.get("/api/translate", params={"code": "Z99.999"})
    c.get("/api/translate", params={"code": "hello there"})          # not a code: not logged
    c.get("/api/translate", params={"code": "99284"})                # found: not logged
    nlm_down(monkeypatch)
    service.clear_cache()
    c.get("/api/translate", params={"code": "E78.5"})                # NLM down: not logged

    with Session() as s:
        rows = [(m.code, m.system, m.times_asked) for m in most_asked(s)]
    assert rows == [("99999", "CPT", 3), ("Z99.999", "ICD-10-CM", 1)]