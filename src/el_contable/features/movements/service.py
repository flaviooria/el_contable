import unicodedata
import uuid
from datetime import date, timedelta
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

        last_available_balance = self._get_stored_balance()

        sorted_rows = sorted(valid_rows, key=lambda r: r.movement_date or date.min, reverse=True)
        deduped_rows = self._dedupe_within_file(sorted_rows)

        existing_keys = self._get_existing_keys(deduped_rows)
        new_rows = [r for r in deduped_rows if self._row_key(r) not in existing_keys]
        skipped_in_db = [r for r in deduped_rows if self._row_key(r) in existing_keys]

        first_balance = valid_rows[0].available_balance if valid_rows else None
        available_balance = (
            first_balance if first_balance is not None else (last_available_balance or 0.0)
        )

        inserted_movements: list[MovementResponse] = []
        skipped_count = len(skipped_in_db) + len(invalid_rows)

        max_existing = self._get_max_order_statement()
        next_order = max_existing + len(new_rows)

        for row in new_rows:
            assert row.amount is not None, "Importe was validated as non-None"
            movement_create = MovementCreate(
                movement_date=row.movement_date or date.today(),
                concept=self.validator.combine_concept(row),
                amount=row.amount or 0.0,
                type=MovementType(self.validator.determine_movement_type(row.amount or 0.0)),
                available_balance=row.available_balance or 0.0,
            )

            movement = Movement(
                account_id=self.account_id,
                movement_date=movement_create.movement_date,
                concept=movement_create.concept,
                amount=movement_create.amount,
                type=movement_create.type,
                available_balance=movement_create.available_balance,
                order_statement=next_order,
            )
            next_order -= 1

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
        md = row.movement_date
        return (md, row.amount, row.available_balance)

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
        movement_dates = [r.movement_date for r in rows if r.movement_date is not None]
        if not movement_dates:
            return set()
        stmt = (
            select(Movement.movement_date, Movement.amount, Movement.available_balance)
            .where(Movement.account_id == self.account_id)
            .where(Movement.movement_date.in_(movement_dates))
        )
        result = self.db.execute(stmt).all()
        keys: set[tuple] = set()
        for r in result:
            keys.add((r.movement_date, r.amount, r.available_balance))
        return keys

    def _get_stored_balance(self) -> float | None:
        if self.account_id is None:
            return None
        return AccountBalanceService(self.db).get_balance(self.account_id)

    def _get_max_order_statement(self) -> int:
        if self.account_id is None:
            return 0
        stmt = select(func.coalesce(func.max(Movement.order_statement), 0)).where(
            Movement.account_id == self.account_id
        )
        return int(self.db.execute(stmt).scalar_one())

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
                Movement.type,
                func.sum(Movement.amount).label("total_amount"),
                func.count().label("movement_count"),
            )
            .where(Movement.account_id == account_id)
            .group_by(Movement.type)
        )
        results = self.db.execute(stmt).all()

        totals_by_type: dict[MovementType, MovementTypeTotals] = {}
        for row in results:
            totals_by_type[row.type] = MovementTypeTotals(
                type=row.type,
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
        normalized concept contains "nomina", ordered by order_statement
        (the single source of chronological truth).

        The period begins strictly after the start-date nómina for income: the
        salary movement and any INGRESO with order_statement less than or equal to
        it are excluded. GASTO movements on start_date remain included.
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

        # Find the closing nómina: first movement after start_date ordered by
        # order_statement (the single source of chronological truth).
        next_day = start_date + timedelta(days=1)
        stmt_next_nomina = (
            select(Movement)
            .where(Movement.account_id == account_id)
            .where(Movement.movement_date >= next_day)
            .order_by(Movement.order_statement)
        )
        all_movements = self.db.execute(stmt_next_nomina).scalars().all()

        closing_nomina: Movement | None = None
        period_end: date | None = None
        for m in all_movements:
            if "nomina" in self._normalize_concept(m.concept):
                closing_nomina = m
                period_end = m.movement_date
                break

        # Query all movements from start_date onwards, ordered by order_statement
        # (the single source of chronological truth).
        query = (
            select(Movement)
            .where(Movement.account_id == account_id)
            .where(Movement.movement_date >= start_date)
            .order_by(Movement.order_statement)
        )
        movements_in_period = self.db.execute(query).scalars().all()

        # If a closing nómina exists, keep only movements that precede it
        # chronologically (break when we reach the closing nómina's order_statement).
        if closing_nomina is not None:
            filtered = []
            for m in movements_in_period:
                if m.order_statement == closing_nomina.order_statement:
                    break
                filtered.append(m)
        else:
            filtered = list(movements_in_period)

        # Exclude the nómina at start_date from income (the period-start salary).
        start_date_nomina = None
        for m in filtered:
            normalized = self._normalize_concept(m.concept)
            if "nomina" in normalized:
                start_date_nomina = m
                break

        if start_date_nomina:
            filtered = [
                m
                for m in filtered
                if m.type != MovementType.INGRESO
                or m.order_statement > start_date_nomina.order_statement
            ]

        income_total = 0.0
        expense_total = 0.0
        income_count = 0
        expense_count = 0

        for m in filtered:
            if m.type == MovementType.INGRESO:
                income_total += m.amount
                income_count += 1
            elif m.type == MovementType.GASTO:
                expense_total += abs(m.amount)
                expense_count += 1

        remaining_balance = round(filtered[-1].available_balance, 2) if filtered else 0.0

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
    def _normalize_concept(concept: str) -> str:
        """Normalize concept by lowercasing and stripping accents."""
        nfkd = unicodedata.normalize("NFKD", concept.lower())
        return "".join(c for c in nfkd if not unicodedata.combining(c))


DatabaseSession = Annotated[Session, Depends(get_db)]


def get_movements_service(
    db: DatabaseSession,
    account_id: uuid.UUID | None = None,
) -> MovementsService:
    parser = MovementsParser()
    validator = MovementsValidator()
    return MovementsService(parser=parser, validator=validator, db=db, account_id=account_id)
