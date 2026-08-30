import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from el_contable.database import get_db
from el_contable.features.account_balance.service import AccountBalanceService
from el_contable.features.movements.models import Movement
from el_contable.features.movements.parser import MovementsParser
from el_contable.features.movements.schemas import (
    MovementCreate,
    MovementResponse,
    MovementRow,
    MovementType,
    UploadResponse,
)
from el_contable.features.movements.validator import MovementsValidator


class MovementsService:
    def __init__(
        self,
        parser: MovementsParser,
        validator: MovementsValidator,
        db: Session,
        account_id: uuid.UUID,
    ):
        self.parser = parser
        self.validator = validator
        self.db = db
        self.account_id = account_id

    def upload(self, file_content: bytes, filename: str) -> UploadResponse:
        rows = self.parser.parse(file_content, filename)

        valid_rows = [r for r in rows if r.is_valid]
        invalid_rows = [r for r in rows if not r.is_valid]

        last_disponible = self._get_stored_balance()

        sorted_rows = sorted(
            valid_rows, key=lambda r: r.fecha_movimiento or datetime.min, reverse=True
        )
        deduped_rows = self._dedupe_within_file(sorted_rows)

        existing_keys = self._get_existing_keys(deduped_rows)
        new_rows = [r for r in deduped_rows if self._row_key(r) not in existing_keys]
        skipped_in_db = [r for r in deduped_rows if self._row_key(r) in existing_keys]

        first_balance = valid_rows[0].disponible if valid_rows else None
        available_balance = first_balance if first_balance is not None else (last_disponible or 0.0)

        inserted_movements: list[MovementResponse] = []
        skipped_count = len(skipped_in_db) + len(invalid_rows)

        for row in new_rows:
            assert row.importe is not None, "Importe was validated as non-None"
            movement_create = MovementCreate(
                fecha_movimiento=row.fecha_movimiento or datetime.now(timezone.utc),
                concepto=self.validator.combine_concept(row),
                importe=row.importe or 0.0,
                tipo=MovementType(self.validator.determine_movement_type(row.importe or 0.0)),
                disponible=row.disponible or 0.0,
            )

            movement = Movement(
                account_id=self.account_id,
                fecha_movimiento=movement_create.fecha_movimiento,
                concepto=movement_create.concepto,
                importe=movement_create.importe,
                tipo=movement_create.tipo,
                disponible=movement_create.disponible,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )

            self.db.add(movement)
            self.db.flush()
            inserted_movements.append(MovementResponse.model_validate(movement))

        balance_service = AccountBalanceService(self.db)
        balance_service.upsert_balance(self.account_id, available_balance)

        self.db.commit()

        return UploadResponse(
            inserted_count=len(inserted_movements),
            skipped_count=skipped_count,
            available_balance=available_balance,
            movements=inserted_movements,
        )

    @staticmethod
    def _row_key(row: MovementRow) -> tuple:
        fecha = row.fecha_movimiento
        if fecha is not None and fecha.tzinfo is not None:
            fecha = fecha.astimezone(timezone.utc).replace(tzinfo=None)
        return (fecha, row.importe, row.disponible)

    def _dedupe_within_file(self, rows: list[MovementRow]) -> list[MovementRow]:
        seen: set[tuple] = set()
        result: list[MovementRow] = []
        for row in rows:
            key = self._row_key(row)
            if key not in seen:
                seen.add(key)
                result.append(row)
        return result

    def _get_existing_keys(self, rows: list[MovementRow]) -> set[tuple]:
        if not rows:
            return set()
        fechas = [r.fecha_movimiento for r in rows if r.fecha_movimiento is not None]
        if not fechas:
            return set()
        stmt = (
            select(Movement.fecha_movimiento, Movement.importe, Movement.disponible)
            .where(Movement.account_id == self.account_id)
            .where(Movement.fecha_movimiento.in_(fechas))
        )
        result = self.db.execute(stmt).all()
        keys: set[tuple] = set()
        for r in result:
            fecha = r.fecha_movimiento
            if fecha.tzinfo is not None:
                fecha = fecha.astimezone(timezone.utc).replace(tzinfo=None)
            keys.add((fecha, r.importe, r.disponible))
        return keys

    def _get_stored_balance(self) -> float | None:
        return AccountBalanceService(self.db).get_balance(self.account_id)

    @staticmethod
    def get_template_path() -> str:
        return "src/el_contable/templates/plantilla_movimientos.xlsx"


DatabaseSession = Annotated[Session, Depends(get_db)]


def get_movements_service(
    db: DatabaseSession,
    account_id: uuid.UUID,
) -> MovementsService:
    parser = MovementsParser()
    validator = MovementsValidator()
    return MovementsService(parser=parser, validator=validator, db=db, account_id=account_id)
