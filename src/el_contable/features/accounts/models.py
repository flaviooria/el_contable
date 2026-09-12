from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from el_contable.database import Base

if TYPE_CHECKING:
    from el_contable.features.account_balance.models import AccountBalance
    from el_contable.features.movements.models import Movement


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_balance: Mapped[float] = mapped_column(Float, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    piggy_banks: Mapped[list[PiggyBank]] = relationship("PiggyBank", back_populates="account")
    movements: Mapped[list[Movement]] = relationship("Movement", back_populates="account")
    account_balance: Mapped[AccountBalance] = relationship(
        "AccountBalance", back_populates="account", uselist=False
    )


class PiggyBank(Base):
    __tablename__ = "piggy_banks"
    __table_args__ = (UniqueConstraint("name", "account_id", name="uq_piggy_bank_name_account"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    account: Mapped[Account] = relationship("Account", back_populates="piggy_banks")
    movements: Mapped[list[Movement]] = relationship(
        "Movement", secondary="movements_piggy_banks", back_populates="piggy_banks"
    )


class MovementPiggyBank(Base):
    __tablename__ = "movements_piggy_banks"

    movement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("movements.id", ondelete="CASCADE"), primary_key=True
    )
    piggy_bank_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("piggy_banks.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
