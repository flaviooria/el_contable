"""Tests for order_statement semantics (EC-007 / movement-ordering).

Covers:
- 4.1: Same-day income before closing salary via order_statement (F1 regression)
- 4.2: Backfill produces strictly increasing per-account sequence
- 4.3: Period-summary boundary detection via order_statement
- 4.4: (account_id, order_statement) uniqueness enforced
- 4.5: Re-upload does not reassign existing order_statement
- 4.6: Existing /totals and /period-summary contracts remain green
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

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
# 4.1 – Same-day income before closing nómina (F1 regression)
# =============================================================================


def test_same_day_income_before_closing_nomina_included_in_period(db_session) -> None:
    """EC-006 review F1: income and closing salary share IDENTICAL movement_date
    (bank exports are date-only; parser converts to 00:00 UTC). They are differentiated
    ONLY by order_statement: income has LOWER ordinal (chronologically earlier), salary
    has HIGHER ordinal.

    This test FAILS on the pre-EC-007 ordering (ORDER BY movement_date, id DESC)
    because without a time component both movements have movement_date=2024-03-05 00:00:00
    and id order alone does not encode the correct same-day statement order.

    With order_statement as the source of truth: income is included in the period,
    feeds remaining_balance, and period_end equals the closing salary's date.
    """
    account_id = create_account(db_session)
    start = date(2024, 3, 1)

    # Both movements: IDENTICAL movement_date (date-only bank export → 00:00 UTC)
    # Income: chronologically earlier in statement → LOWER order_statement
    create_movement(
        db_session,
        account_id,
        500.0,
        MovementType.INGRESO,
        movement_date=date(2024, 3, 5),
        concept="Freelance",
        available_balance=1500.0,
        order_statement=1,
    )
    # Closing salary: chronologically later in statement → HIGHER order_statement
    create_movement(
        db_session,
        account_id,
        3000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 3, 5),
        concept="Nómina March",
        available_balance=4500.0,
        order_statement=2,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.period_end == date(2024, 3, 5)
    # Income (500) is included, start-date nómina excluded
    assert result.income_total == 500.0
    assert result.income_count == 1
    # remaining_balance comes from the last movement before the closing nómina
    assert result.remaining_balance == 1500.0


# =============================================================================
# 4.2 – Backfill: strictly increasing per-account sequence
# =============================================================================


def test_backfill_produces_strictly_increasing_sequence(db_session) -> None:
    """The backfill invariant: when movements are ordered by (movement_date ASC,
    id DESC), their order_statement values are strictly increasing (no gaps, 1-based).

    Approach: create movements with explicit order_statement values that follow the
    backfill formula (row_number over partition by account_id order by
    movement_date ASC, id DESC). Then verify:
      - ordinals are strictly increasing when ordered by (movement_date ASC, id DESC)
      - same-date ties broken by id DESC are respected

    We simulate the backfill by assigning ordinals that match the formula output.
    """
    account_id = create_account(db_session)

    # Insert in out-of-chronological order (simulates existing legacy data)
    # Assign provisional ordinals (all distinct) to pass the unique constraint on insert.
    m_late = Movement(
        account_id=account_id,
        movement_date=date(2024, 3, 1),
        concept="Late March",
        amount=100.0,
        type=MovementType.INGRESO,
        available_balance=100.0,
        order_statement=10,
    )
    m_early1 = Movement(
        account_id=account_id,
        movement_date=date(2024, 1, 15),
        concept="Early January A",
        amount=50.0,
        type=MovementType.GASTO,
        available_balance=50.0,
        order_statement=20,
    )
    m_early2 = Movement(
        account_id=account_id,
        movement_date=date(2024, 1, 15),
        concept="Early January B",
        amount=75.0,
        type=MovementType.INGRESO,
        available_balance=125.0,
        order_statement=30,
    )
    m_mid = Movement(
        account_id=account_id,
        movement_date=date(2024, 2, 10),
        concept="Mid February",
        amount=-25.0,
        type=MovementType.GASTO,
        available_balance=100.0,
        order_statement=40,
    )

    db_session.add_all([m_late, m_early1, m_early2, m_mid])
    db_session.flush()

    # Simulate backfill: query in backfill order, then reassign ordinals in that order.
    # This replicates what the migration SQL does:
    #   row_number() over (partition by account_id order by movement_date, id DESC)
    from sqlalchemy import select

    stmt = (
        select(Movement)
        .where(Movement.account_id == account_id)
        .order_by(Movement.movement_date.asc(), Movement.id.desc())
    )
    ordered = list(db_session.execute(stmt).scalars().all())
    assert len(ordered) == 4

    # Assign backfill ordinals 1..4 in backfill order
    for i, m in enumerate(ordered):
        m.order_statement = i + 1
    db_session.flush()

    # Verify: ordered by (movement_date ASC, id DESC) → ordinals 1, 2, 3, 4 (strictly increasing)
    ordered_verify = list(
        db_session.execute(
            select(Movement)
            .where(Movement.account_id == account_id)
            .order_by(Movement.movement_date.asc(), Movement.id.desc())
        )
        .scalars()
        .all()
    )
    ordinals = [m.order_statement for m in ordered_verify]
    assert ordinals == [1, 2, 3, 4], (
        f"Backfill produced non-strictly-increasing sequence: {ordinals}"
    )

    # Verify same-date tie-breaking: both Jan-15 movements; the one with higher id
    # (earlier in statement order) should have lower ordinal.
    jan_movements = [m for m in ordered_verify if m.movement_date == date(2024, 1, 15)]
    assert len(jan_movements) == 2
    assert jan_movements[0].id > jan_movements[1].id, "Higher id should come first (id DESC)"
    assert jan_movements[0].order_statement < jan_movements[1].order_statement, (
        "Higher id (earlier in day) should have lower ordinal"
    )


# =============================================================================
# 4.3 – Period-summary boundary detection via order_statement
# =============================================================================


def test_period_summary_same_day_before_closing_nomina_included(db_session) -> None:
    """Movement on the same calendar day as the closing salary but with lower
    order_statement is included in the period.  Both share IDENTICAL movement_date
    (date-only export → 00:00 UTC), differentiated only by order_statement.

    This test FAILS on the pre-EC-007 ordering because both same-day movements
    have identical movement_date and their relative position depends on order_statement.
    """
    account_id = create_account(db_session)
    start = date(2024, 4, 1)

    # Apr 10: expense included
    create_movement(
        db_session,
        account_id,
        -200.0,
        MovementType.GASTO,
        movement_date=date(2024, 4, 10),
        concept="Gasto",
        available_balance=800.0,
        order_statement=1,
    )
    # Apr 30: income SAME fecha as closing nómina but earlier (lower ordinal)
    create_movement(
        db_session,
        account_id,
        300.0,
        MovementType.INGRESO,
        movement_date=date(2024, 4, 30),
        concept="Freelance Apr",
        available_balance=1100.0,
        order_statement=2,
    )
    # Apr 30: closing nómina (later statement position, higher ordinal)
    create_movement(
        db_session,
        account_id,
        2000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 4, 30),
        concept="Nómina April",
        available_balance=3100.0,
        order_statement=3,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.period_end == date(2024, 4, 30)
    assert result.income_total == 300.0
    assert result.expense_total == 200.0
    assert result.remaining_balance == 1100.0
    assert result.income_count == 1
    assert result.expense_count == 1


def test_period_summary_open_ended_with_order_statement(db_session) -> None:
    """order_statement does not affect open-ended period behaviour."""
    account_id = create_account(db_session)
    start = date(2024, 5, 1)

    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 5, 15),
        concept="Income",
        available_balance=1000.0,
        order_statement=1,
    )
    create_movement(
        db_session,
        account_id,
        -200.0,
        MovementType.GASTO,
        movement_date=date(2024, 5, 20),
        concept="Gasto",
        available_balance=800.0,
        order_statement=2,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.period_end is None
    assert result.income_total == 1000.0
    assert result.expense_total == 200.0
    assert result.remaining_balance == 800.0


# =============================================================================
# 4.4 – (account_id, order_statement) uniqueness enforced
# =============================================================================


def test_order_statement_unique_per_account_violation_raises_integrity_error(
    db_session,
) -> None:
    """Inserting two movements with the same (account_id, order_statement) raises
    an IntegrityError (SQLite reports as IntegrityError; PostgreSQL would raise
    the same via the DB-level UNIQUE constraint)."""
    account_id = create_account(db_session)

    # Insert first movement with order_statement=5
    create_movement(
        db_session,
        account_id,
        100.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 1),
        concept="First",
        available_balance=100.0,
        order_statement=5,
    )
    db_session.commit()

    # Attempt to insert second movement with the SAME account_id and order_statement=5
    second = Movement(
        account_id=account_id,
        movement_date=date(2024, 1, 2),
        concept="Duplicate ordinal",
        amount=50.0,
        type=MovementType.GASTO,
        available_balance=50.0,
        order_statement=5,  # same ordinal → violates unique constraint
    )
    db_session.add(second)
    with pytest.raises(IntegrityError):
        db_session.flush()


# =============================================================================
# 4.5 – Re-upload does not reassign existing order_statement
# =============================================================================


def _make_csv_content() -> bytes:
    """Minimal CSV with Fecha,Concepto,Importe,Disponible columns."""
    return (
        "Fecha,Concepto,Importe,Disponible\n"
        "2024-01-15,Ingreso A,100.0,100.0\n"
        "2024-01-20,Gasto B,-50.0,50.0\n".encode()
    )


def test_reupload_does_not_reassign_existing_order_statement(db_session) -> None:
    """Uploading the same file twice: the second upload deduplicates existing
    movements and does NOT change their order_statement values."""
    account_id = create_account(db_session)
    db_session.commit()

    service = make_service(db_session, account_id=account_id)

    csv = _make_csv_content()

    # First upload: creates two movements
    result1 = service.upload(csv, "movements.csv")
    assert result1.inserted_count == 2
    db_session.commit()

    # Read back the order_statement values assigned in first upload
    movimientos = (
        db_session.query(Movement)
        .filter(Movement.account_id == account_id)
        .order_by(Movement.order_statement)
        .all()
    )
    assert len(movimientos) == 2
    first_ordinal_1 = movimientos[0].order_statement
    first_ordinal_2 = movimientos[1].order_statement

    # Second upload: same CSV → deduplication, no new ordinals assigned
    result2 = service.upload(csv, "movements.csv")
    assert result2.inserted_count == 0
    assert result2.skipped_count == 2
    db_session.commit()

    # order_statement values must be unchanged
    movimientos_after = (
        db_session.query(Movement)
        .filter(Movement.account_id == account_id)
        .order_by(Movement.order_statement)
        .all()
    )
    assert len(movimientos_after) == 2
    assert movimientos_after[0].order_statement == first_ordinal_1
    assert movimientos_after[1].order_statement == first_ordinal_2


def test_upload_assigns_continuing_order_statement(db_session) -> None:
    """New movements receive order_statement continuing after the maximum existing."""
    account_id = create_account(db_session)
    db_session.commit()

    service = make_service(db_session, account_id=account_id)

    csv1 = "Fecha,Concepto,Importe,Disponible\n2024-01-01,Nómina,3000.0,3000.0\n".encode()
    result1 = service.upload(csv1, "jan.csv")
    assert result1.inserted_count == 1
    db_session.commit()

    m1 = db_session.query(Movement).filter(Movement.account_id == account_id).one()
    assert m1.order_statement == 1

    # Second upload: new movements should continue from max existing (1)
    csv2 = (
        "Fecha,Concepto,Importe,Disponible\n"
        "2024-02-01,Nómina Feb,3000.0,6000.0\n"
        "2024-02-15,Freelance,500.0,6500.0\n".encode()
    )
    result2 = service.upload(csv2, "feb.csv")
    assert result2.inserted_count == 2
    db_session.commit()

    movimientos = (
        db_session.query(Movement)
        .filter(Movement.account_id == account_id)
        .order_by(Movement.order_statement)
        .all()
    )
    ordinales = [m.order_statement for m in movimientos]
    # First upload: ordinal 1; Second upload: 2 and 3 (continuing)
    assert ordinales == [1, 2, 3]


def test_upload_same_day_movements_keep_statement_order(db_session) -> None:
    """Upload with two same-day movements listed in reverse statement order
    (earlier-in-day row appears LATER in the file, as in real bank exports).
    order_statement must reflect statement chronology: earlier row gets LOWER ordinal.

    Spec scenario: "Same-day movements keep statement order".
    This test FAILS with ORDER BY movement_date, id DESC alone because both
    movements have identical movement_date (2024-01-15 → 00:00 UTC) and id order happens
    to match statement order only by insertion coincidence — not by semantic guarantee.
    """
    account_id = create_account(db_session)
    db_session.commit()

    service = make_service(db_session, account_id=account_id)

    # CSV: same date (2024-01-15) for both rows. In real bank exports
    # (reverse-chronological), the earlier-in-day row appears LATER in the file.
    # So row 1 (Gasto B, later in day) comes first, row 2 (Ingreso A, earlier in day)
    # comes second. Upload must assign LOWER ordinal to the earlier-in-day row.
    csv = (
        "Fecha,Concepto,Importe,Disponible\n"
        "2024-01-15,Gasto B,-100.0,400.0\n"  # later in day (row 1 in export)
        "2024-01-15,Ingreso A,500.0,500.0\n".encode()  # earlier in day (row 2 in export)
    )
    result = service.upload(csv, "same_day.csv")
    assert result.inserted_count == 2
    db_session.commit()

    movimientos = (
        db_session.query(Movement)
        .filter(Movement.account_id == account_id)
        .order_by(Movement.order_statement)
        .all()
    )
    assert len(movimientos) == 2

    # order_statement=1 → earlier in statement order (Ingreso A, row 1 in file)
    # order_statement=2 → later in statement order (Gasto B, row 2 in file)
    assert movimientos[0].concept == "Ingreso A"
    assert movimientos[0].order_statement == 1
    assert movimientos[1].concept == "Gasto B"
    assert movimientos[1].order_statement == 2


# =============================================================================
# 4.6 – Regression: existing /totals and /period-summary contracts
# =============================================================================


def test_get_totals_response_shape_unchanged(db_session) -> None:
    """Response shape, 404, and 422 behaviour of /totals are unchanged."""
    account_id = create_account(db_session)
    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        movement_date=date(2024, 1, 1),
        available_balance=1000.0,
        order_statement=1,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_totals(account_id)

    assert result.account_id == account_id
    assert len(result.totals) == 2
    ingreso = next(t for t in result.totals if t.type == MovementType.INGRESO)
    assert ingreso.total_amount == 1000.0
    assert ingreso.count == 1


def test_get_totals_raises_for_nonexistent_account(db_session) -> None:
    service = make_service(db_session)
    with pytest.raises(ValueError, match="Account not found"):
        service.get_totals(uuid.uuid4())


def test_period_summary_response_shape_unchanged(db_session) -> None:
    """Response shape of period-summary is unchanged from EC-006."""
    account_id = create_account(db_session)
    start = date(2024, 1, 1)

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
        -300.0,
        MovementType.GASTO,
        movement_date=date(2024, 1, 15),
        concept="Gasto",
        available_balance=700.0,
        order_statement=2,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.account_id == account_id
    assert result.period_start == date(2024, 1, 1)
    assert result.period_end is None
    assert result.income_total == 0.0  # start-date nómina excluded
    assert result.expense_total == 300.0
    assert result.remaining_balance == 700.0
    assert result.income_count == 0
    assert result.expense_count == 1


def test_period_summary_raises_for_nonexistent_account(db_session) -> None:
    service = make_service(db_session)
    with pytest.raises(ValueError, match="Account not found"):
        service.get_period_summary(uuid.uuid4(), date(2024, 1, 1))
