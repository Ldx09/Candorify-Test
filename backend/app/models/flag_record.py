"""Database table `bill_flags`: the check engine's flags for a stored bill, with an id and a status
the user controls. Column names must match Nathalie's schema."""
import json
from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.engine.models import Flag

FlagStatus = Literal["investigating", "add_to_letter", "dismissed"]
DEFAULT_STATUS: FlagStatus = "investigating"


class FlagRecord(Base):
    __tablename__ = "bill_flags"
    __table_args__ = (UniqueConstraint("bill_id", "rule", "line_no", "question_id", name="uq_bill_flag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), index=True)
    rule: Mapped[str] = mapped_column(String(40))
    line_no: Mapped[int | None] = mapped_column(Integer)          # None for the subtotal flag
    code: Mapped[str | None] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    expected: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    actual: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    related_line_no: Mapped[int | None] = mapped_column(Integer)
    line_numbers: Mapped[str] = mapped_column(Text, default="[]")  # JSON list, e.g. "[1, 3]"
    question_id: Mapped[str | None] = mapped_column(String(80))    # answer_mismatch flags only
    letter_text: Mapped[str | None] = mapped_column(Text)          # answer_mismatch flags only
    status: Mapped[str] = mapped_column(String(20), default=DEFAULT_STATUS)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())

    def to_flag(self) -> Flag:
        return Flag(id=self.id, status=self.status, rule=self.rule, line_no=self.line_no, code=self.code,
                    message=self.message, expected=self.expected, actual=self.actual,
                    related_line_no=self.related_line_no, line_numbers=json.loads(self.line_numbers or "[]"),
                    question_id=self.question_id, letter_text=self.letter_text)