from datetime import datetime

from sqlalchemy import DateTime, Float, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AccountBalance(Base):
    __tablename__ = "account_balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
