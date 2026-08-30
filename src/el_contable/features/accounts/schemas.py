import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountBase(BaseModel):
    base_balance: float
    entry_date: date


class AccountCreate(AccountBase):
    pass


class AccountResponse(AccountBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PiggyBankBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    max_balance: float | None = None


class PiggyBankCreate(PiggyBankBase):
    pass


class PiggyBankResponse(PiggyBankBase):
    id: uuid.UUID
    account_id: uuid.UUID
    current_balance: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PiggyBankWithProgress(PiggyBankResponse):
    progress: float | None = None


class AccountWithPiggyBanks(AccountResponse):
    piggy_banks: list[PiggyBankResponse] = []
