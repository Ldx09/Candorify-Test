"""The `users` table plus the queries the rest of the backend uses.
Column names must match Nathalie's schema exactly."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Premium plan (Stripe). Card details are never stored here: Stripe keeps them.
    plan: Mapped[str | None] = mapped_column(String(20), default="free")            # "free" | "premium"
    plan_status: Mapped[str | None] = mapped_column(String(30))                      # Stripe status: active, past_due, canceled...
    plan_renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # end of the paid year
    plan_cancel_at_period_end: Mapped[bool | None] = mapped_column(Boolean, default=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))

    @property
    def is_premium(self) -> bool:
        return self.plan == "premium"

def create_user(db: Session, email: str, password_hash: str, full_name: str | None = None) -> User:
    """Inserts a new user. Raises sqlalchemy IntegrityError if the email already exists."""
    user = User(email=email.lower(), password_hash=password_hash, full_name=full_name)
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)