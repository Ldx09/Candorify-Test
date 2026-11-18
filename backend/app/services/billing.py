"""Premium plan billing with Stripe (embedded Checkout, yearly subscription).

The flow:
  1. POST /api/billing/checkout   -> a Checkout Session (ui_mode embedded_page); the page mounts Stripe's form.
  2. The user pays inside Stripe's form. We never see or store card details.
  3. Stripe sends the user back to checkout.html?session_id=...; GET /api/billing/session/{id} confirms it
     and turns Premium on right away (so it also works locally without webhooks).
  4. Webhooks (POST /api/billing/webhook) keep the plan in sync afterwards: renewals, failed payments,
     cancellations.
Premium doesn't lock any feature yet: it only sets users.plan = "premium".
"""
import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

log = logging.getLogger("candorify.billing")

PREMIUM_STATUSES = {"active", "trialing", "past_due"}   # past_due: Stripe is still retrying the card
PRODUCT_NAME = "Candorify Premium"
BRANDING = {   # makes Stripe's form match Candorify (forest green, square corners, Inter)
    "display_name": "Candorify",
    "button_color": "#1F3B2D",
    "background_color": "#FAF6EE",
    "border_style": "rectangular",
    "font_family": "inter",
}


class BillingError(Exception):
    """A problem we can explain to the user (shown as the error message)."""


def enabled() -> bool:
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PUBLISHABLE_KEY)


def test_mode() -> bool:
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_test_"))


def _client():
    if not enabled():
        raise BillingError("Payments aren't set up on this server yet.")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _get(obj, key, default=None):
    """Reads a field from a Stripe object or a plain dict (webhook payloads)."""
    try:
        value = obj[key]
    except (KeyError, TypeError, AttributeError):
        return default
    return default if value is None else value


def _line_item() -> dict:
    if settings.STRIPE_PRICE_ID:
        return {"price": settings.STRIPE_PRICE_ID, "quantity": 1}
    return {"quantity": 1, "price_data": {
        "currency": "usd", "unit_amount": settings.PREMIUM_PRICE_CENTS,
        "recurring": {"interval": settings.PREMIUM_INTERVAL},
        "product_data": {"name": PRODUCT_NAME,
                         "description": "Every charge explained in your language, and letters about specific charges."},
    }}


def _customer_id(db: Session, user: User) -> str:
    s = _client()
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = s.Customer.create(email=user.email, name=user.full_name or None,
                                 metadata={"candorify_user_id": str(user.id)})
    user.stripe_customer_id = customer["id"]
    db.commit()
    return user.stripe_customer_id


def create_checkout(db: Session, user: User, return_base: str) -> str:
    """Starts a Checkout Session for Premium and returns its client secret."""
    if user.is_premium:
        raise BillingError("You're already on Premium.")
    s = _client()
    session = s.checkout.Session.create(
        ui_mode="embedded_page",
        mode="subscription",
        customer=_customer_id(db, user),
        client_reference_id=str(user.id),
        line_items=[_line_item()],
        return_url=return_base.rstrip("/") + "/checkout.html?session_id={CHECKOUT_SESSION_ID}",
        metadata={"candorify_user_id": str(user.id)},
        subscription_data={"metadata": {"candorify_user_id": str(user.id)}},
        branding_settings=BRANDING,
    )
    return session["client_secret"]


def _period_end(sub) -> datetime | None:
    # Newer Stripe API versions keep the period on the subscription item; older ones on the subscription.
    end = _get(sub, "current_period_end")
    if end is None:
        items = _get(_get(sub, "items", {}), "data", []) or []
        if items:
            end = _get(items[0], "current_period_end")
    return datetime.fromtimestamp(int(end), tz=timezone.utc) if end else None


def apply_subscription(db: Session, user: User, sub) -> None:
    """Copies a Stripe subscription's state onto the user."""
    status = _get(sub, "status")
    user.stripe_subscription_id = _get(sub, "id")
    user.plan_status = status
    user.plan = "premium" if status in PREMIUM_STATUSES else "free"
    user.plan_renews_at = _period_end(sub)
    user.plan_cancel_at_period_end = bool(_get(sub, "cancel_at_period_end", False) or _get(sub, "cancel_at"))
    if status not in PREMIUM_STATUSES:
        user.plan_cancel_at_period_end = False
    db.commit()
    log.info("User %s plan=%s status=%s", user.id, user.plan, status)


def confirm_session(db: Session, user: User, session_id: str) -> dict:
    """Checks a finished Checkout Session (after Stripe sends the user back) and turns Premium on."""
    s = _client()
    try:
        session = s.checkout.Session.retrieve(session_id, expand=["subscription"])
    except stripe.InvalidRequestError:
        raise BillingError("We couldn't find that payment.") from None
    owner = _get(session, "client_reference_id") or _get(_get(session, "metadata", {}), "candorify_user_id")
    if str(owner) != str(user.id):
        raise BillingError("That payment belongs to another account.")
    status = _get(session, "status")                     # open | complete | expired
    if status == "complete":
        sub = _get(session, "subscription")
        if isinstance(sub, str):
            sub = s.Subscription.retrieve(sub)
        if sub:
            if not user.stripe_customer_id:
                user.stripe_customer_id = _get(session, "customer")
            apply_subscription(db, user, sub)
    details = _get(session, "customer_details", {}) or {}
    return {"status": status, "email": _get(details, "email"), "amount_total": _get(session, "amount_total")}


def set_cancel(db: Session, user: User, cancel: bool) -> None:
    """Cancel renewal (Premium stays until the paid year ends), or undo that."""
    if not user.stripe_subscription_id or not user.is_premium:
        raise BillingError("You don't have an active Premium plan.")
    s = _client()
    sub = s.Subscription.modify(user.stripe_subscription_id, cancel_at_period_end=cancel)
    apply_subscription(db, user, sub)


def _user_for(db: Session, obj) -> User | None:
    uid = _get(_get(obj, "metadata", {}), "candorify_user_id") or _get(obj, "client_reference_id")
    if uid and str(uid).isdigit():
        user = db.get(User, int(uid))
        if user:
            return user
    customer = _get(obj, "customer")
    if customer:
        return db.scalar(select(User).where(User.stripe_customer_id == customer))
    return None


def handle_event(db: Session, event) -> str:
    """Applies one verified webhook event. Returns what was done (for logs and tests)."""
    kind = _get(event, "type")
    obj = _get(_get(event, "data", {}), "object", {})
    if kind == "checkout.session.completed" and _get(obj, "mode") == "subscription":
        user = _user_for(db, obj)
        if not user:
            return "ignored: unknown user"
        sub = _get(obj, "subscription")
        if isinstance(sub, str):
            sub = _client().Subscription.retrieve(sub)
        if not user.stripe_customer_id:
            user.stripe_customer_id = _get(obj, "customer")
        apply_subscription(db, user, sub)
        return "premium on"
    if kind in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        user = _user_for(db, obj)
        if not user:
            return "ignored: unknown user"
        apply_subscription(db, user, obj)
        return f"plan {user.plan}"
    if kind in ("invoice.paid", "invoice.payment_failed"):
        user = _user_for(db, obj)
        if user and user.stripe_subscription_id:
            apply_subscription(db, user, _client().Subscription.retrieve(user.stripe_subscription_id))
            return f"plan {user.plan}"
        return "ignored: unknown user"
    return "ignored"


def cancel_now_quietly(user: User) -> None:
    """When an account is deleted: stop its subscription right away so it's never charged again.
    Never blocks the deletion (Stripe errors are only logged)."""
    if not (enabled() and user.stripe_subscription_id and user.plan_status in PREMIUM_STATUSES):
        return
    try:
        _client().Subscription.cancel(user.stripe_subscription_id)
    except stripe.StripeError as e:
        log.warning("Couldn't cancel subscription for deleted user %s: %s", user.id, e)