from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from el_contable.database import Base

if TYPE_CHECKING:
    from el_contable.features.accounts.models import Account


class AccountBalance(Base):
    __tablename__ = "account_balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    account: Mapped[Account] = relationship("Account", back_populates="account_balance")
