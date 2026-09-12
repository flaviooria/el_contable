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
    amount: float,
    movement_type: MovementType,
    movement_date: date | None = None,
    concept: str = "Test movement",
    available_balance: float | None = None,
    order_statement: int = 1,
) -> Movement:
    movement = Movement(
        account_id=account_id,
        movement_date=movement_date or datetime.now(timezone.utc).date(),
        concept=concept,
        amount=amount,
        type=movement_type,
        available_balance=available_balance if available_balance is not None else amount,
        order_statement=order_statement,
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
        movement_date=date(2024, 1, 1),
        concept="Nómina January",
        available_balance=1000.0,
        order_statement=1,
    )
    # Other income in period
    create_movement(
        db_session,
        account_id,
        200.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 15),
        concept="Freelance payment",
        available_balance=1200.0,
        order_statement=2,
    )
    # Expense in period (negative amount per DB convention)
    create_movement(
        db_session,
        account_id,
        -150.0,
        MovementType.GASTO,
        movement_date=date(2024, 1, 20),
        concept="Groceries",
        available_balance=1050.0,
        order_statement=3,
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
        movement_date=date(2024, 1, 1),
        concept="Nómina",
        available_balance=3000.0,
        order_statement=1,
    )
    # Another income later
    create_movement(
        db_session,
        account_id,
        500.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 10),
        concept="Bonus",
        available_balance=3500.0,
        order_statement=2,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.income_total == 500.0
    assert result.income_count == 1
    assert result.remaining_balance == 3500.0


def test_period_summary_excludes_same_day_pre_nomina_income(db_session) -> None:
    """EC-008: income on start_date with ordinal <= start-nómina ordinal is excluded
    from income_total and income_count (even though it is chronologically part of
    the same calendar day).  A later income within the period IS included.

    Scenario: "Income before the start nómina on start_date".
    Uses IDENTICAL movement_date for start-date movements to force reliance on
    order_statement (no time-component discrimination).
    """
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

    # Jan 1: income chronologically BEFORE the start nómina on same day (no "nomina" in label) → EXCLUDED
    create_movement(
        db_session,
        account_id,
        500.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 1),
        concept="Pago freelance anticipado",
        available_balance=3500.0,
        order_statement=1,
    )
    # Jan 1: start-date nómina → EXCLUDED
    create_movement(
        db_session,
        account_id,
        3000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 1),
        concept="Nómina January",
        available_balance=3500.0,
        order_statement=2,
    )
    # Jan 15: later income in period → INCLUDED
    create_movement(
        db_session,
        account_id,
        200.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 15),
        concept="Freelance",
        available_balance=3700.0,
        order_statement=3,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    # Only the Jan 15 income counts; pre-nómina and start nómina are both excluded
    assert result.income_total == 200.0
    assert result.income_count == 1
    # remaining_balance is the available_balance of the last movement before the closing salary
    # (or the last included movement when there is no closing salary)
    assert result.remaining_balance == 3700.0


def test_period_summary_includes_same_day_pre_nomina_gasto(db_session) -> None:
    """EC-008: a gasto on start_date with ordinal <= start-nómina ordinal remains
    INCLUDED in expense_total and expense_count (asymmetric boundary: only income
    is excluded before the start nómina; gastos are always kept).

    Scenario: "Expense before the start nómina on start_date".
    Uses IDENTICAL movement_date for start-date movements.
    """
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

    # Jan 1: gasto chronologically BEFORE the start nómina on same day → INCLUDED
    create_movement(
        db_session,
        account_id,
        -100.0,
        MovementType.GASTO,
        movement_date=date(2024, 1, 1),
        concept="Gasto supermercado",
        available_balance=2900.0,
        order_statement=1,
    )
    # Jan 1: start-date nómina → EXCLUDED from income only
    create_movement(
        db_session,
        account_id,
        3000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 1),
        concept="Nómina January",
        available_balance=3000.0,
        order_statement=2,
    )
    # Jan 10: another gasto in period → INCLUDED
    create_movement(
        db_session,
        account_id,
        -50.0,
        MovementType.GASTO,
        movement_date=date(2024, 1, 10),
        concept="Gasto Jan 10",
        available_balance=2850.0,
        order_statement=3,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    # Both gastos are included: pre-nómina (ordinal 1) AND Jan 10 (ordinal 3)
    assert result.expense_total == 150.0
    assert result.expense_count == 2
    # No income in period (start nómina excluded; no other income)
    assert result.income_total == 0.0
    assert result.income_count == 0
    # remaining_balance from last included movement (Jan 10 gasto)
    assert result.remaining_balance == 2850.0


def test_period_summary_includes_same_day_post_nomina_income(db_session) -> None:
    """EC-008: an ingreso on start_date with ordinal > start-nómina ordinal remains
    INCLUDED in income_total and income_count.

    Scenario: "Income after the start nómina on start_date".
    Uses IDENTICAL movement_date for both start-date movements.
    """
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

    # Jan 1: start-date nómina → EXCLUDED
    create_movement(
        db_session,
        account_id,
        3000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 1),
        concept="Nómina January",
        available_balance=3000.0,
        order_statement=1,
    )
    # Jan 1: income AFTER the start nómina on same day (no "nomina" in label) → INCLUDED
    create_movement(
        db_session,
        account_id,
        500.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 1),
        concept="Ingreso posterior",
        available_balance=3500.0,
        order_statement=2,
    )
    # Jan 20: another income later in period → INCLUDED
    create_movement(
        db_session,
        account_id,
        200.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 20),
        concept="Freelance",
        available_balance=3700.0,
        order_statement=3,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    # Both post-nómina income and later income are included
    assert result.income_total == 700.0
    assert result.income_count == 2
    assert result.remaining_balance == 3700.0


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
        movement_date=date(2024, 2, 5),
        concept="Some income",
        available_balance=100.0,
        order_statement=1,
    )
    create_movement(
        db_session,
        account_id,
        -50.0,
        MovementType.GASTO,
        movement_date=date(2024, 2, 10),
        concept="Some expense",
        available_balance=50.0,
        order_statement=2,
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
        movement_date=date(2024, 1, 1),
        concept="Nómina",
        available_balance=1000.0,
        order_statement=1,
    )
    # Movement in period (negative amount per DB convention)
    create_movement(
        db_session,
        account_id,
        -200.0,
        MovementType.GASTO,
        movement_date=date(2024, 1, 15),
        concept="Groceries",
        available_balance=800.0,
        order_statement=2,
    )
    # Next nómina on Feb 1 (closes the period)
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 2, 1),
        concept="Nómina February",
        available_balance=1800.0,
        order_statement=3,
    )
    # Movement after period end (should not be included)
    create_movement(
        db_session,
        account_id,
        -300.0,
        MovementType.GASTO,
        movement_date=date(2024, 2, 5),
        concept="Other expense",
        available_balance=1500.0,
        order_statement=4,
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
        movement_date=date(2024, 1, 1),
        concept="Salary January",  # No accent
        available_balance=1000.0,
        order_statement=1,
    )
    # Next "nomina" without accent
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 2, 1),
        concept="nomina February",  # Lowercase, no accent
        available_balance=2000.0,
        order_statement=2,
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
        movement_date=date(2024, 1, 1),
        concept="Nómina",
        available_balance=1000.0,
        order_statement=1,
    )
    create_movement(
        db_session,
        account_id,
        -3232.239999999999,
        MovementType.GASTO,
        movement_date=date(2024, 1, 15),
        concept="Big expense",
        available_balance=-2232.239999999999,
        order_statement=2,
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

    order_statement is the source of chronological truth. The same-day income has
    a lower order_statement (chronologically earlier) than the closing nómina.
    """
    account_id = create_account(db_session)
    start = date(2024, 2, 1)

    # Feb 1: start-date salary (excluded from income)
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 2, 1),
        concept="Nómina February",
        available_balance=1000.0,
        order_statement=1,
    )
    # Feb 10: expense (available_balance after: 600.0)
    create_movement(
        db_session,
        account_id,
        -400.0,
        MovementType.GASTO,
        movement_date=date(2024, 2, 10),
        concept="Groceries",
        available_balance=600.0,
        order_statement=2,
    )
    # Mar 1: same-day income (chronologically BEFORE the closing salary → lower order_statement)
    create_movement(
        db_session,
        account_id,
        591.11,
        MovementType.INGRESO,
        movement_date=date(2024, 3, 1),
        concept="Refund",
        available_balance=591.11,
        order_statement=3,
    )
    # Mar 1: closing salary (chronologically AFTER the income → higher order_statement)
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 3, 1),
        concept="Nómina March",
        available_balance=1600.0,
        order_statement=4,
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
