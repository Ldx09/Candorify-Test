"""Request/response shapes for auth: this is the contract the frontend builds against."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=255)
    remember_me: bool = False  # "keep me signed in": ~30-day login instead of ~1 day

    @field_validator("password")
    @classmethod
    def password_rules(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password is too long")
        if v.strip() != v or not v.strip():
            raise ValueError("Password cannot start or end with spaces")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False  # "keep me signed in": ~30-day login instead of ~1 day


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int        # seconds until the token expires
    expires_at: datetime   # when the token expires (UTC)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    plan: str = "free"                         # "free" | "premium"
    plan_status: str | None = None             # Stripe's status, e.g. "active", "past_due"
    plan_renews_at: datetime | None = None     # when the paid year ends (renews, or ends if canceled)
    plan_cancel_at_period_end: bool = False    # True: canceled, Premium stays until plan_renews_at

    model_config = {"from_attributes": True}

    @field_validator("plan", mode="before")
    @classmethod
    def _plan(cls, v):
        return v or "free"

    @field_validator("plan_cancel_at_period_end", mode="before")
    @classmethod
    def _cancel(cls, v):
        return bool(v)

class SignupResponse(UserOut):
    """The new user plus a token, so the user is signed in right after creating the account."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: datetime