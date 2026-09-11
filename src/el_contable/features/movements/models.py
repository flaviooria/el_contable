from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from el_contable.database import Base
from el_contable.features.movements.schemas import MovementType

if TYPE_CHECKING:
    from el_contable.features.accounts.models import Account, PiggyBank


class Movement(Base):
    __tablename__ = "movements"
    __table_args__ = (
        UniqueConstraint("account_id", "orden_extracto", name="uq_movements_account_orden"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    fecha_movimiento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    concepto: Mapped[str] = mapped_column(String(500), nullable=False)
    importe: Mapped[float] = mapped_column(Float, nullable=False)
    tipo: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    disponible: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        nullable=False,
    )
    orden_extracto: Mapped[int] = mapped_column(Integer, nullable=False)
    account: Mapped["Account"] = relationship("Account", back_populates="movements")
    piggy_banks: Mapped[list[PiggyBank]] = relationship(
        "PiggyBank", secondary="movements_piggy_banks", back_populates="movements"
    )
