from sqlalchemy import select
from sqlalchemy.orm import Session

from el_contable.features.account_balance.models import AccountBalance


class AccountBalanceService:
    def __init__(self, db: Session):
        self.db = db

    def get_balance(self) -> float | None:
        stmt = select(AccountBalance).limit(1)
        result = self.db.execute(stmt)
        row = result.scalar_one_or_none()
        return row.balance if row else None

    def upsert_balance(self, balance: float) -> None:
        stmt = select(AccountBalance).limit(1)
        result = self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            self.db.add(AccountBalance(balance=balance))
        else:
            existing.balance = balance
