import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from el_contable.database import get_db
from el_contable.features.accounts.schemas import (
    AccountCreate,
    AccountResponse,
    PiggyBankCreate,
    PiggyBankResponse,
    PiggyBankWithProgress,
)
from el_contable.features.accounts.service import AccountService, get_account_service

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    data: AccountCreate,
    service: Annotated[AccountService, Depends(get_account_service)],
    db: DatabaseSession,
) -> AccountResponse:
    account = service.create_account(data)
    db.commit()
    return AccountResponse.model_validate(account)


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: uuid.UUID,
    service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    account = service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return AccountResponse.model_validate(account)


@router.post(
    "/{account_id}/piggy-banks",
    response_model=PiggyBankResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_piggy_bank(
    account_id: uuid.UUID,
    data: PiggyBankCreate,
    service: Annotated[AccountService, Depends(get_account_service)],
    db: DatabaseSession,
) -> PiggyBankResponse:
    account = service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    piggy_bank = service.create_piggy_bank(account_id, data)
    db.commit()
    return PiggyBankResponse.model_validate(piggy_bank)


@router.get("/{account_id}/piggy-banks", response_model=list[PiggyBankWithProgress])
def list_piggy_banks(
    account_id: uuid.UUID,
    service: Annotated[AccountService, Depends(get_account_service)],
) -> list[PiggyBankWithProgress]:
    return service.get_piggy_banks_by_account(account_id)
