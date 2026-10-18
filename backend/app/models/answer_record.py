"""Database table `bill_answers`: the patient's answers to the follow-up questions (used for flags and
for the accuracy page). Column names must match Nathalie's schema."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnswerRecord(Base):
    __tablename__ = "bill_answers"
    __table_args__ = (UniqueConstraint("bill_id", "question_id", name="uq_bill_answer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(String(80))     # e.g. "room_nights", "supplies_received:A6402"
    question_type: Mapped[str] = mapped_column(String(40))   # e.g. "room_nights", "supplies_received"
    value: Mapped[str | None] = mapped_column(Text)          # English label or number as text; None = skipped
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())