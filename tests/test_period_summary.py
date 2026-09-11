import uuid
from datetime import date, datetime, timezone

import pytest

from el_contable.features.accounts.models import Account
from el_contable.features.movements.models import Movement
from el_contable.features.movements.schemas import MovementType
from el_contable.features.movements.service import MovementsService
from el_contable.features.movements.parser import MovementsParser
from el_contable.features.movements.validator import MovementsValidator


def make_service(db_session, account_id: uuid.UUID | None = None) -> MovementsService:
    return MovementsService(
        parser=MovementsParser(),
        validator=MovementsValidator(),
        db=db_session,
        account_id=account_id,
    )


def create_account(db_session, base_balance: float = 0.0) -> uuid.UUID:
    account = Account(base_balance=base_balance, entry_date=datetime.now(timezone.utc).date())
    db_session.add(account)
    db_session.flush()
    return account.id


def create_movement(
    db_session,
    account_id: uuid.UUID,
    importe: float,
    tipo: MovementType,
    fecha: datetime | None = None,
    concepto: str = "Test movement",
    disponible: float | None = None,
    orden_extracto: int = 1,
) -> Movement:
    movement = Movement(
        account_id=account_id,
        fecha_movimiento=fecha or datetime.now(timezone.utc),
        concepto=concepto,
        importe=importe,
        tipo=tipo,
        disponible=disponible if disponible is not None else importe,
        expires_at=datetime.now(timezone.utc),
        orden_extracto=orden_extracto,
    )
    db_session.add(movement)
    db_session.flush()
    return movement


# =============================================================================
# Service-level tests
# =============================================================================


def test_period_summary_returns_correct_totals(db_session) -> None:
    """Period with income and expense movements returns correct sums."""
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

    # Start-date salary (should be excluded from income)
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
        concepto="Nómina January",
        disponible=1000.0,
        orden_extracto=1,
    )
    # Other income in period
    create_movement(
        db_session,
        account_id,
        200.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        concepto="Freelance payment",
        disponible=1200.0,
        orden_extracto=2,
    )
    # Expense in period (negative importe per DB convention)
    create_movement(
        db_session,
        account_id,
        -150.0,
        MovementType.GASTO,
        fecha=datetime(2024, 1, 20, 12, 0, tzinfo=timezone.utc),
        concepto="Groceries",
        disponible=1050.0,
        orden_extracto=3,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.account_id == account_id
    assert result.period_start == date(2024, 1, 1)
    assert result.period_end is None  # No next nómina
    assert result.income_total == 200.0  # Excludes start-date nómina
    assert result.expense_total == 150.0
    assert result.income_count == 1
    assert result.expense_count == 1
    assert result.remaining_balance == 1050.0


def test_period_summary_excludes_start_nomina_from_income(db_session) -> None:
    """The salary movement at start_date is excluded from income_total."""
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

    # Nómina at start_date
    create_movement(
        db_session,
        account_id,
        3000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        concepto="Nómina",
        disponible=3000.0,
        orden_extracto=1,
    )
    # Another income later
    create_movement(
        db_session,
        account_id,
        500.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 1, 10, 0, 0, tzinfo=timezone.utc),
        concepto="Bonus",
        disponible=3500.0,
        orden_extracto=2,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.income_total == 500.0
    assert result.income_count == 1
    assert result.remaining_balance == 3500.0


def test_period_summary_zero_totals_when_no_movements(db_session) -> None:
    """Period with no movements returns zero totals."""
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.account_id == account_id
    assert result.period_start == date(2024, 1, 1)
    assert result.period_end is None
    assert result.income_total == 0.0
    assert result.expense_total == 0.0
    assert result.income_count == 0
    assert result.expense_count == 0
    assert result.remaining_balance == 0.0


def test_period_summary_open_ended_period(db_session) -> None:
    """Period with no next nómina is open-ended (period_end is null)."""
    account_id = create_account(db_session)
    start = date(2024, 2, 1)

    create_movement(
        db_session,
        account_id,
        100.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 2, 5, 0, 0, tzinfo=timezone.utc),
        concepto="Some income",
        disponible=100.0,
        orden_extracto=1,
    )
    create_movement(
        db_session,
        account_id,
        -50.0,
        MovementType.GASTO,
        fecha=datetime(2024, 2, 10, 0, 0, tzinfo=timezone.utc),
        concepto="Some expense",
        disponible=50.0,
        orden_extracto=2,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.period_end is None
    assert result.income_total == 100.0
    assert result.expense_total == 50.0


def test_period_summary_bounded_by_next_nomina(db_session) -> None:
    """Period ends the day before the next nómina movement."""
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

    # Start-date salary
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        concepto="Nómina",
        disponible=1000.0,
        orden_extracto=1,
    )
    # Movement in period (negative importe per DB convention)
    create_movement(
        db_session,
        account_id,
        -200.0,
        MovementType.GASTO,
        fecha=datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc),
        concepto="Groceries",
        disponible=800.0,
        orden_extracto=2,
    )
    # Next nómina on Feb 1 (closes the period)
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 2, 1, 0, 0, tzinfo=timezone.utc),
        concepto="Nómina February",
        disponible=1800.0,
        orden_extracto=3,
    )
    # Movement after period end (should not be included)
    create_movement(
        db_session,
        account_id,
        -300.0,
        MovementType.GASTO,
        fecha=datetime(2024, 2, 5, 0, 0, tzinfo=timezone.utc),
        concepto="Other expense",
        disponible=1500.0,
        orden_extracto=4,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.period_start == date(2024, 1, 1)
    assert result.period_end == date(2024, 2, 1)
    assert result.income_total == 0.0  # Excludes start-date nómina, no other income
    assert result.expense_total == 200.0  # Only Jan 15 expense
    assert result.remaining_balance == 800.0


def test_period_summary_nomina_without_accent(db_session) -> None:
    """A movement with 'nomina' (no accent) also closes the period."""
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        concepto="Salary January",  # No accent
        disponible=1000.0,
        orden_extracto=1,
    )
    # Next "nomina" without accent
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 2, 1, 0, 0, tzinfo=timezone.utc),
        concepto="nomina February",  # Lowercase, no accent
        disponible=2000.0,
        orden_extracto=2,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.period_end == date(2024, 2, 1)


def test_period_summary_rounds_monetary_values(db_session) -> None:
    """All monetary values are rounded to 2 decimals to eliminate float noise."""
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

    # Expense with float precision noise: -3232.239999999999 rounds to 3232.24
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        concepto="Nómina",
        disponible=1000.0,
        orden_extracto=1,
    )
    create_movement(
        db_session,
        account_id,
        -3232.239999999999,
        MovementType.GASTO,
        fecha=datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc),
        concepto="Big expense",
        disponible=-2232.239999999999,
        orden_extracto=2,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    # income_total excludes start-date nómina = 0.0
    assert result.income_total == 0.0
    # expense_total should be the absolute sum rounded to 2 decimals
    assert result.expense_total == 3232.24
    # remaining_balance should be rounded to 2 decimals
    assert result.remaining_balance == -2232.24


def test_period_summary_same_day_as_closing_nomina(db_session) -> None:
    """A movement on the same calendar day as the closing nómina but chronologically
    before the salary credit IS included in the period.

    orden_extracto is the source of chronological truth. The same-day income has
    a lower orden_extracto (chronologically earlier) than the closing nómina.
    """
    account_id = create_account(db_session)
    start = date(2024, 2, 1)

    # Feb 1: start-date salary (excluded from income)
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 2, 1, 0, 0, tzinfo=timezone.utc),
        concepto="Nómina February",
        disponible=1000.0,
        orden_extracto=1,
    )
    # Feb 10: gasto (disponible after: 600.0)
    create_movement(
        db_session,
        account_id,
        -400.0,
        MovementType.GASTO,
        fecha=datetime(2024, 2, 10, 0, 0, tzinfo=timezone.utc),
        concepto="Groceries",
        disponible=600.0,
        orden_extracto=2,
    )
    # Mar 1: same-day income (chronologically BEFORE the closing nómina → lower orden_extracto)
    create_movement(
        db_session,
        account_id,
        591.11,
        MovementType.INGRESO,
        fecha=datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc),
        concepto="Refund",
        disponible=591.11,
        orden_extracto=3,
    )
    # Mar 1: closing nómina (chronologically AFTER the income → higher orden_extracto)
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 3, 1, 11, 0, tzinfo=timezone.utc),
        concepto="Nómina March",
        disponible=1600.0,
        orden_extracto=4,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.period_end == date(2024, 3, 1)
    # remaining_balance is the disponible of the last movement before the closing nómina
    assert result.remaining_balance == 591.11
    # income_total includes the same-day income (591.11), excludes start-date nómina
    assert result.income_total == 591.11
    # expense_total is the absolute sum
    assert result.expense_total == 400.0
    assert result.income_count == 1
    assert result.expense_count == 1


def test_period_summary_raises_error_for_nonexistent_account(db_session) -> None:
    """ValueError is raised when account does not exist."""
    nonexistent_id = uuid.uuid4()
    service = make_service(db_session)

    with pytest.raises(ValueError, match="Account not found"):
        service.get_period_summary(nonexistent_id, date(2024, 1, 1))


# =============================================================================
# HTTP contract tests (TestClient / integration tests)
# =============================================================================


def test_get_period_summary_returns_404_for_nonexistent_account(client) -> None:
    """GET /api/v1/movements/period-summary?account_id=<nonexistent> returns HTTP 404."""
    nonexistent_id = uuid.uuid4()
    response = client.get(
        f"/api/v1/movements/period-summary?account_id={nonexistent_id}&start_date=2024-01-01"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Account not found"}


def test_get_period_summary_returns_422_when_account_id_missing(client) -> None:
    """GET /api/v1/movements/period-summary (no account_id) returns HTTP 422."""
    response = client.get("/api/v1/movements/period-summary?start_date=2024-01-01")

    assert response.status_code == 422


def test_get_period_summary_returns_422_when_start_date_missing(client) -> None:
    """GET /api/v1/movements/period-summary (no start_date) returns HTTP 422."""
    account_id = uuid.uuid4()
    response = client.get(f"/api/v1/movements/period-summary?account_id={account_id}")

    assert response.status_code == 422
