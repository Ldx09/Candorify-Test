"""Premium plan with Stripe. See app/services/billing.py for the whole flow.

    GET  /api/billing/config           public: is Premium available, price, Stripe publishable key
    POST /api/billing/checkout         login: start embedded Checkout -> {client_secret}
    GET  /api/billing/session/{id}     login: confirm a finished payment, turns Premium on
    POST /api/billing/cancel           login: stop renewal (Premium stays until the paid year ends)
    POST /api/billing/resume           login: undo the cancel
    POST /api/billing/webhook          Stripe only (signature checked)
"""
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import UserOut
from app.services import billing

log = logging.getLogger("candorify.billing")

public_router = APIRouter(prefix="/api/billing", tags=["billing"])
router = APIRouter(prefix="/billing", tags=["billing"])   # mounted under /api with login required


class BillingConfig(BaseModel):
    enabled: bool
    test_mode: bool
    publishable_key: str | None
    price_cents: int
    interval: str


class CheckoutOut(BaseModel):
    client_secret: str


class SessionOut(BaseModel):
    status: str | None            # "complete" | "open" | "expired"
    email: str | None = None
    amount_total: int | None = None
    user: UserOut


def _fail(err: billing.BillingError):
    raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err)) from None


def _stripe_down(err: Exception):
    log.warning("Stripe error: %s", err)
    raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The payment service didn't respond. Please try again.") from None


def _return_base(request: Request) -> str:
    """Send people back to the site they paid from, if it's one of ours."""
    origin = request.headers.get("origin")
    allowed = set(settings.CORS_ORIGINS) | {settings.FRONTEND_URL.rstrip("/")}
    return origin if origin in allowed else settings.FRONTEND_URL


@public_router.get("/config", response_model=BillingConfig)
def config():
    return BillingConfig(enabled=billing.enabled(), test_mode=billing.test_mode(),
                         publishable_key=settings.STRIPE_PUBLISHABLE_KEY if billing.enabled() else None,
                         price_cents=settings.PREMIUM_PRICE_CENTS, interval=settings.PREMIUM_INTERVAL)


@router.post("/checkout", response_model=CheckoutOut)
def checkout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return CheckoutOut(client_secret=billing.create_checkout(db, user, _return_base(request)))
    except billing.BillingError as e:
        _fail(e)
    except stripe.StripeError as e:
        _stripe_down(e)


@router.get("/session/{session_id}", response_model=SessionOut)
def session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not session_id.startswith("cs_") or len(session_id) > 255:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That isn't a payment link.")
    try:
        out = billing.confirm_session(db, user, session_id)
    except billing.BillingError as e:
        _fail(e)
    except stripe.StripeError as e:
        _stripe_down(e)
    db.refresh(user)
    return SessionOut(**out, user=UserOut.model_validate(user))


@router.post("/cancel", response_model=UserOut)
def cancel(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        billing.set_cancel(db, user, True)
    except billing.BillingError as e:
        _fail(e)
    except stripe.StripeError as e:
        _stripe_down(e)
    return user


@router.post("/resume", response_model=UserOut)
def resume(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        billing.set_cancel(db, user, False)
    except billing.BillingError as e:
        _fail(e)
    except stripe.StripeError as e:
        _stripe_down(e)
    return user


@public_router.post("/webhook", include_in_schema=False)
async def webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Webhooks aren't set up")
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, request.headers.get("stripe-signature", ""),
                                               settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid signature") from None
    try:
        result = billing.handle_event(db, event)
    except stripe.StripeError as e:
        log.warning("Webhook %s failed: %s", event["type"], e)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Try again") from None   # Stripe retries later
    log.info("Webhook %s: %s", event["type"], result)
    return {"received": True}