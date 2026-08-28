from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, Enum, Float, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from el_contable.features.movements.schemas import MovementType


class Base(DeclarativeBase):
    pass


class Movement(Base):
    __tablename__ = "movements"

    id: Mapped[int] = mapped_column(primary_key=True)
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
