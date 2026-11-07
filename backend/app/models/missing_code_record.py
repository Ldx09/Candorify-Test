"""Database table `missing_codes`: billing codes people looked up that we couldn't explain, and how often.
Used to decide which codes to add next. No user, bill or personal data is stored here."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MissingCodeRecord(Base):
    __tablename__ = "missing_codes"
    __table_args__ = (UniqueConstraint("code", "system", name="uq_missing_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    system: Mapped[str] = mapped_column(String(20))       # CPT, HCPCS, ICD-10-CM, Revenue code
    times_asked: Mapped[int] = mapped_column(Integer, default=1)
    first_asked: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_asked: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())