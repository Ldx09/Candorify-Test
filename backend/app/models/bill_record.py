"""Database tables for stored bills: `bills` and `bill_lines`. Column names must match Nathalie's schema.
(The plain Bill / LineItem models in bill.py and line_item.py are what the check engine runs on.)"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.bill import Bill
from app.models.line_item import LineItem


class BillRecord(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str | None] = mapped_column(String(100))  # e.g. "ER visit Sept" or "BILL-001"
    stated_subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["BillLineRecord"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan", order_by="BillLineRecord.line_no")

    def to_engine_bill(self) -> Bill:
        """Converts the stored bill into the model the check engine runs on."""
        return Bill(
            bill_id=str(self.id),
            stated_subtotal=self.stated_subtotal,
            lines=[LineItem(line_no=ln.line_no, code=ln.code, description=ln.description,
                            quantity=ln.quantity, unit_price=ln.unit_price, line_total=ln.line_total)
                   for ln in self.lines],
        )


class BillLineRecord(Base):
    __tablename__ = "bill_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    bill: Mapped[BillRecord] = relationship(back_populates="lines")