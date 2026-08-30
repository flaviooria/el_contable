import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from el_contable.database import get_db
from el_contable.features.accounts.models import Account, PiggyBank
from el_contable.features.accounts.models import MovementPiggyBank
from el_contable.features.accounts.schemas import (
    AccountCreate,
    PiggyBankCreate,
    PiggyBankWithProgress,
)
from el_contable.features.movements.models import Movement


class AccountService:
    def __init__(self, db: Session):
        self.db = db

    def create_account(self, data: AccountCreate) -> Account:
        account = Account(
            base_balance=data.base_balance,
            entry_date=data.entry_date,
        )
        self.db.add(account)
        self.db.flush()
        return account

    def get_account(self, account_id: uuid.UUID) -> Account | None:
        stmt = select(Account).where(Account.id == account_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_piggy_bank_balance(self, piggy_bank_id: uuid.UUID) -> float:
        stmt = (
            select(func.coalesce(func.sum(Movement.importe), 0.0))
            .select_from(MovementPiggyBank)
            .join(Movement, MovementPiggyBank.movement_id == Movement.id)
            .where(MovementPiggyBank.piggy_bank_id == piggy_bank_id)
        )
        result = self.db.execute(stmt).scalar()
        return float(result) if result is not None else 0.0

    def create_piggy_bank(self, account_id: uuid.UUID, data: PiggyBankCreate) -> PiggyBank:
        piggy_bank = PiggyBank(
            account_id=account_id,
            name=data.name,
            max_balance=data.max_balance,
        )
        self.db.add(piggy_bank)
        self.db.flush()
        return piggy_bank

    def get_piggy_banks_by_account(self, account_id: uuid.UUID) -> list[PiggyBankWithProgress]:
        stmt = select(PiggyBank).where(PiggyBank.account_id == account_id)
        piggy_banks = self.db.execute(stmt).scalars().all()

        result = []
        for pb in piggy_banks:
            current_balance = self.get_piggy_bank_balance(pb.id)
            progress = None
            if pb.max_balance is not None and pb.max_balance > 0:
                progress = min(100.0, (current_balance / pb.max_balance) * 100.0)

            result.append(
                PiggyBankWithProgress(
                    id=pb.id,
                    account_id=pb.account_id,
                    name=pb.name,
                    max_balance=pb.max_balance,
                    current_balance=current_balance,
                    progress=progress,
                    created_at=pb.created_at,
                )
            )
        return result

    def link_movement_to_piggy_bank(
        self, movement_id: int, piggy_bank_id: uuid.UUID
    ) -> MovementPiggyBank:
        link = MovementPiggyBank(
            movement_id=movement_id,
            piggy_bank_id=piggy_bank_id,
        )
        self.db.add(link)
        self.db.flush()
        return link


DatabaseSession = Annotated[Session, Depends(get_db)]


def get_account_service(db: DatabaseSession) -> AccountService:
    return AccountService(db=db)
