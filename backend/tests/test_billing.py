"""Premium plan with Stripe. Stripe is faked here: no network, no real keys, nothing charged.
Run: pytest -q tests/test_billing.py"""
import os
import tempfile
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

import pytest
import stripe
from fastapi.testclient import TestClient

import server
from app.core.config import settings

RENEWS = int(time.time()) + 365 * 24 * 3600


def sub(status="active", cancel=False, sid="sub_1", customer="cus_1", user_id="1"):
    # newer Stripe API versions keep current_period_end on the subscription item
    return {"id": sid, "status": status, "customer": customer, "cancel_at_period_end": cancel,
            "metadata": {"candorify_user_id": user_id}, "items": {"data": [{"current_period_end": RENEWS}]}}


class FakeStripe:
    def __init__(self):
        self.created = []
        self.sessions = {}
        self.subs = {}
        self.canceled = []

    def install(self, mp):
        mp.setattr(stripe.Customer, "create", lambda **kw: {"id": "cus_1"})

        def create_session(**kw):
            self.created.append(kw)
            sid = f"cs_test_{len(self.created)}"
            self.sessions[sid] = {"id": sid, "client_reference_id": kw["client_reference_id"], "status": "open",
                                  "customer": kw["customer"], "subscription": None, "amount_total": 4999,
                                  "customer_details": {"email": "pay@example.com"}, "metadata": kw["metadata"]}
            return {"id": sid, "client_secret": sid + "_secret"}
        mp.setattr(stripe.checkout.Session, "create", create_session)

        def retrieve_session(sid, **kw):
            if sid not in self.sessions:
                raise stripe.InvalidRequestError("No such session", "id")
            return self.sessions[sid]
        mp.setattr(stripe.checkout.Session, "retrieve", retrieve_session)
        mp.setattr(stripe.Subscription, "retrieve", lambda sid, **kw: self.subs[sid])

        def modify(sid, cancel_at_period_end):
            self.subs[sid]["cancel_at_period_end"] = cancel_at_period_end
            return self.subs[sid]
        mp.setattr(stripe.Subscription, "modify", modify)
        mp.setattr(stripe.Subscription, "cancel", lambda sid, **kw: self.canceled.append(sid))

    def pay(self, sid, user_id):
        self.subs["sub_1"] = sub(user_id=str(user_id))
        self.sessions[sid].update(status="complete", subscription="sub_1")


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(settings, "STRIPE_PUBLISHABLE_KEY", "pk_test_fake")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_fake")
    f = FakeStripe()
    f.install(monkeypatch)
    return f


def login(client, email):
    r = client.post("/api/auth/signup", json={"email": email, "password": "s3cretpass1", "accept_terms": True})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["id"]


def test_config_without_keys_says_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", None)
    monkeypatch.setattr(settings, "STRIPE_PUBLISHABLE_KEY", None)
    with TestClient(server.app) as c:
        cfg = c.get("/api/billing/config").json()
        assert cfg["enabled"] is False and cfg["publishable_key"] is None and cfg["price_cents"] == 4999
        h, _ = login(c, "nokeys@example.com")
        r = c.post("/api/billing/checkout", headers=h)
        assert r.status_code == 400 and "aren't set up" in r.json()["detail"]


def test_checkout_pay_confirm_cancel_resume(fake):
    with TestClient(server.app) as c:
        h, uid = login(c, "buyer@example.com")
        assert c.get("/api/me", headers=h).json()["plan"] == "free"
        cfg = c.get("/api/billing/config").json()
        assert cfg == {"enabled": True, "test_mode": True, "publishable_key": "pk_test_fake",
                       "price_cents": 4999, "interval": "year"}
        assert c.post("/api/billing/checkout").status_code == 401                  # login needed

        r = c.post("/api/billing/checkout", headers={**h, "Origin": "http://evil.example"})
        assert r.status_code == 200 and r.json()["client_secret"] == "cs_test_1_secret"
        kw = fake.created[0]
        assert kw["ui_mode"] == "embedded_page" and kw["mode"] == "subscription"
        assert kw["return_url"].startswith(settings.FRONTEND_URL) and "{CHECKOUT_SESSION_ID}" in kw["return_url"]
        item = kw["line_items"][0]["price_data"]
        assert item["unit_amount"] == 4999 and item["recurring"] == {"interval": "year"}

        open_ = c.get("/api/billing/session/cs_test_1", headers=h).json()             # not paid yet
        assert open_["status"] == "open" and open_["user"]["plan"] == "free"

        fake.pay("cs_test_1", uid)
        done = c.get("/api/billing/session/cs_test_1", headers=h).json()
        assert done["status"] == "complete" and done["user"]["plan"] == "premium"
        assert done["user"]["plan_renews_at"] and done["email"] == "pay@example.com"
        me = c.get("/api/me", headers=h).json()
        assert me["plan"] == "premium" and me["plan_status"] == "active" and not me["plan_cancel_at_period_end"]

        assert c.post("/api/billing/checkout", headers=h).status_code == 400          # already Premium
        out = c.post("/api/billing/cancel", headers=h).json()
        assert out["plan"] == "premium" and out["plan_cancel_at_period_end"] is True   # stays until the year ends
        assert c.post("/api/billing/resume", headers=h).json()["plan_cancel_at_period_end"] is False


def test_other_users_session_and_bad_ids(fake):
    with TestClient(server.app) as c:
        h1, uid1 = login(c, "a1@example.com")
        h2, _ = login(c, "a2@example.com")
        c.post("/api/billing/checkout", headers=h1)
        sid = f"cs_test_{len(fake.created)}"
        fake.pay(sid, uid1)
        r = c.get(f"/api/billing/session/{sid}", headers=h2)
        assert r.status_code == 400 and "another account" in r.json()["detail"]
        assert c.get("/api/me", headers=h2).json()["plan"] == "free"
        assert c.get("/api/billing/session/nope", headers=h1).status_code == 400
        assert c.get("/api/billing/session/cs_missing", headers=h1).status_code == 400
        assert c.post("/api/billing/cancel", headers=h2).status_code == 400            # nothing to cancel


def test_webhooks_keep_the_plan_in_sync(fake, monkeypatch):
    events = []
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: events.pop(0))
    with TestClient(server.app) as c:
        h, uid = login(c, "hook@example.com")
        fake.subs["sub_1"] = sub(user_id=str(uid))
        events.append({"type": "checkout.session.completed", "data": {"object": {
            "mode": "subscription", "client_reference_id": str(uid), "customer": "cus_1", "subscription": "sub_1",
            "metadata": {"candorify_user_id": str(uid)}}}})
        assert c.post("/api/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1"}).status_code == 200
        assert c.get("/api/me", headers=h).json()["plan"] == "premium"

        events.append({"type": "customer.subscription.updated", "data": {"object": sub("past_due", user_id=str(uid))}})
        c.post("/api/billing/webhook", content=b"{}")
        assert c.get("/api/me", headers=h).json()["plan_status"] == "past_due"         # still Premium while retrying

        events.append({"type": "customer.subscription.deleted", "data": {"object": sub("canceled", user_id=str(uid))}})
        c.post("/api/billing/webhook", content=b"{}")
        me = c.get("/api/me", headers=h).json()
        assert me["plan"] == "free" and me["plan_status"] == "canceled"

        events.append({"type": "something.else", "data": {"object": {}}})
        assert c.post("/api/billing/webhook", content=b"{}").status_code == 200


def test_webhook_rejects_bad_signature(fake, monkeypatch):
    def bad(*a, **k):
        raise stripe.SignatureVerificationError("bad", "sig")
    monkeypatch.setattr(stripe.Webhook, "construct_event", bad)
    with TestClient(server.app) as c:
        assert c.post("/api/billing/webhook", content=b"{}", headers={"stripe-signature": "x"}).status_code == 400


def test_deleting_account_stops_the_subscription(fake):
    with TestClient(server.app) as c:
        h, uid = login(c, "leaver@example.com")
        c.post("/api/billing/checkout", headers=h)
        sid = f"cs_test_{len(fake.created)}"
        fake.pay(sid, uid)
        c.get(f"/api/billing/session/{sid}", headers=h)
        assert c.delete("/api/me", headers=h).status_code == 204
        assert fake.canceled == ["sub_1"]