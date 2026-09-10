import unicodedata
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from el_contable.database import get_db
from el_contable.features.account_balance.service import AccountBalanceService
from el_contable.features.accounts.models import Account
from el_contable.features.movements.models import Movement
from el_contable.features.movements.parser import MovementsParser
from el_contable.features.movements.schemas import (
    MovementCreate,
    MovementResponse,
    MovementRow,
    MovementTotalsResponse,
    MovementType,
    MovementTypeTotals,
    PeriodSummaryResponse,
    UploadResponse,
)
from el_contable.features.movements.validator import MovementsValidator


class MovementsService:
    def __init__(
        self,
        parser: MovementsParser,
        validator: MovementsValidator,
        db: Session,
        account_id: uuid.UUID | None = None,
    ):
        self.parser = parser
        self.validator = validator
        self.db = db
        self.account_id = account_id

    def upload(self, file_content: bytes, filename: str) -> UploadResponse:
        assert self.account_id is not None, "account_id is required for upload"
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
        if self.account_id is None:
            return None
        return AccountBalanceService(self.db).get_balance(self.account_id)

    @staticmethod
    def get_template_path() -> str:
        return "src/el_contable/templates/plantilla_movimientos.xlsx"

    def get_totals(self, account_id: uuid.UUID) -> MovementTotalsResponse:
        """Get accumulated movement amounts grouped by type for an account.

        Args:
            account_id: The UUID of the account to get totals for.

        Returns:
            MovementTotalsResponse with totals grouped by movement type.

        Raises:
            ValueError: If the account does not exist.
        """
        account_exists = self.db.execute(
            select(func.count()).select_from(Account).where(Account.id == account_id)
        ).scalar_one()

        if account_exists == 0:
            raise ValueError("Account not found")

        stmt = (
            select(
                Movement.tipo,
                func.sum(Movement.importe).label("total_amount"),
                func.count().label("movement_count"),
            )
            .where(Movement.account_id == account_id)
            .group_by(Movement.tipo)
        )
        results = self.db.execute(stmt).all()

        totals_by_type: dict[MovementType, MovementTypeTotals] = {}
        for row in results:
            totals_by_type[row.tipo] = MovementTypeTotals(
                type=row.tipo,
                total_amount=row.total_amount or 0.0,
                count=row.movement_count,
            )

        all_types = [MovementType.INGRESO, MovementType.GASTO]
        for movement_type in all_types:
            if movement_type not in totals_by_type:
                totals_by_type[movement_type] = MovementTypeTotals(
                    type=movement_type,
                    total_amount=0.0,
                    count=0,
                )

        sorted_totals = [totals_by_type[t] for t in all_types]

        return MovementTotalsResponse(account_id=account_id, totals=sorted_totals)

    def get_period_summary(
        self,
        account_id: uuid.UUID,
        start_date: date,
    ) -> PeriodSummaryResponse:
        """Get accumulated income, expenses, and balance for a pay period.

        The period starts on start_date and ends on the closing nómina movement
        (exclusive end boundary). If no such movement exists after start_date,
        the period is open-ended (period_end is null).

        The closing nómina is the first movement strictly after start_date whose
        normalized concepto contains "nomina". Movements on the same calendar day
        as the closing nómina are included only if they occur chronologically before
        it (determined by id order for same-timestamp rows).

        The salary movement at start_date is excluded from income totals.
        Expense totals are reported as positive numbers (absolute sum).

        All monetary values (income_total, expense_total, remaining_balance)
        are rounded to 2 decimal places to eliminate float noise.

        Args:
            account_id: The UUID of the account.
            start_date: The start date of the period.

        Returns:
            PeriodSummaryResponse with income/expense totals and remaining balance.

        Raises:
            ValueError: If the account does not exist.
        """
        account_exists = self.db.execute(
            select(func.count()).select_from(Account).where(Account.id == account_id)
        ).scalar_one()

        if account_exists == 0:
            raise ValueError("Account not found")

        # Find the closing nómina: first movement after start_date whose
        # normalized concepto contains "nomina". Keep the movement object.
        next_day = datetime.combine(start_date + timedelta(days=1), datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        stmt_next_nomina = (
            select(Movement)
            .where(Movement.account_id == account_id)
            .where(Movement.fecha_movimiento >= next_day)
            .order_by(Movement.fecha_movimiento)
        )
        all_movements = self.db.execute(stmt_next_nomina).scalars().all()

        closing_nomina: Movement | None = None
        period_end: date | None = None
        for m in all_movements:
            if "nomina" in self._normalize_concepto(m.concepto):
                closing_nomina = m
                period_end = m.fecha_movimiento.date()
                break

        # Query all movements from start_date onwards, ordered chronologically.
        # For same-timestamp rows (date-only bank exports), id DESC reconstructs
        # statement order because later-in-day salary rows were inserted first.
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        query = (
            select(Movement)
            .where(Movement.account_id == account_id)
            .where(Movement.fecha_movimiento >= start_dt)
            .order_by(Movement.fecha_movimiento, Movement.id.desc())
        )
        movements_in_period = self.db.execute(query).scalars().all()

        # If a closing nómina exists, keep only movements that precede it
        # chronologically (break when we reach the closing nómina id).
        if closing_nomina is not None:
            filtered = []
            for m in movements_in_period:
                if m.id == closing_nomina.id:
                    break
                filtered.append(m)
        else:
            filtered = list(movements_in_period)

        # Exclude the nómina at start_date from income (the period-start salary).
        start_date_nomina = None
        for m in filtered:
            normalized = self._normalize_concepto(m.concepto)
            if "nomina" in normalized:
                start_date_nomina = m
                break

        if start_date_nomina:
            filtered = [m for m in filtered if m.id != start_date_nomina.id]

        income_total = 0.0
        expense_total = 0.0
        income_count = 0
        expense_count = 0

        for m in filtered:
            if m.tipo == MovementType.INGRESO:
                income_total += m.importe
                income_count += 1
            elif m.tipo == MovementType.GASTO:
                expense_total += abs(m.importe)
                expense_count += 1

        remaining_balance = round(filtered[-1].disponible, 2) if filtered else 0.0

        return PeriodSummaryResponse(
            account_id=account_id,
            period_start=start_date,
            period_end=period_end,
            income_total=round(income_total, 2),
            expense_total=round(expense_total, 2),
            remaining_balance=remaining_balance,
            income_count=income_count,
            expense_count=expense_count,
        )

    @staticmethod
    def _normalize_concepto(concepto: str) -> str:
        """Normalize concepto by lowercasing and stripping accents."""
        nfkd = unicodedata.normalize("NFKD", concepto.lower())
        return "".join(c for c in nfkd if not unicodedata.combining(c))


DatabaseSession = Annotated[Session, Depends(get_db)]


def get_movements_service(
    db: DatabaseSession,
    account_id: uuid.UUID | None = None,
) -> MovementsService:
    parser = MovementsParser()
    validator = MovementsValidator()
    return MovementsService(parser=parser, validator=validator, db=db, account_id=account_id)
