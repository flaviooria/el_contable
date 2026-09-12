from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from el_contable.database import Base
from el_contable.features.movements.schemas import MovementType

if TYPE_CHECKING:
    from el_contable.features.accounts.models import Account, PiggyBank


class Movement(Base):
    __tablename__ = "movements"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "order_statement",
            name="uq_movements_account_order_statement",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    concept: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    available_balance: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    order_statement: Mapped[int] = mapped_column(Integer, nullable=False)
    account: Mapped["Account"] = relationship("Account", back_populates="movements")
    piggy_banks: Mapped[list[PiggyBank]] = relationship(
        "PiggyBank", secondary="movements_piggy_banks", back_populates="movements"
    )
