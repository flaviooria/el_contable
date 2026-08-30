import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from el_contable.features.account_balance.models import AccountBalance


class AccountBalanceService:
    def __init__(self, db: Session):
        self.db = db

    def get_balance(self, account_id: uuid.UUID) -> float | None:
        stmt = select(AccountBalance).where(AccountBalance.account_id == account_id)
        result = self.db.execute(stmt)
        row = result.scalar_one_or_none()
        return row.balance if row else None

    def upsert_balance(self, account_id: uuid.UUID, balance: float) -> None:
        stmt = select(AccountBalance).where(AccountBalance.account_id == account_id)
        result = self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            self.db.add(AccountBalance(account_id=account_id, balance=balance))
        else:
            existing.balance = balance
