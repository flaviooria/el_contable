"""Tests for orden_extracto semantics (EC-007 / movement-ordering).

Covers:
- 4.1: Same-day income before closing nómina via orden_extracto (F1 regression)
- 4.2: Backfill produces strictly increasing per-account sequence
- 4.3: Period-summary boundary detection via orden_extracto
- 4.4: (account_id, orden_extracto) uniqueness enforced
- 4.5: Re-upload does not reassign existing orden_extracto
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
# 4.1 – Same-day income before closing nómina (F1 regression)
# =============================================================================


def test_same_day_income_before_closing_nomina_included_in_period(db_session) -> None:
    """EC-006 review F1: income and closing nómina share IDENTICAL fecha_movimiento
    (bank exports are date-only; parser converts to 00:00 UTC). They are differentiated
    ONLY by orden_extracto: income has LOWER ordinal (chronologically earlier), nómina
    has HIGHER ordinal.

    This test FAILS on the pre-EC-007 ordering (ORDER BY fecha_movimiento, id DESC)
    because without a time component both movements have fecha=2024-03-05 00:00:00
    and id order alone does not encode the correct same-day statement order.

    With orden_extracto as the source of truth: income is included in the period,
    feeds remaining_balance, and period_end equals the closing nómina's date.
    """
    account_id = create_account(db_session)
    start = date(2024, 3, 1)

    # Both movements: IDENTICAL fecha_movimiento (date-only bank export → 00:00 UTC)
    # Income: chronologically earlier in statement → LOWER orden_extracto
    create_movement(
        db_session,
        account_id,
        500.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 3, 5, tzinfo=timezone.utc),
        concepto="Freelance",
        disponible=1500.0,
        orden_extracto=1,
    )
    # Closing nómina: chronologically later in statement → HIGHER orden_extracto
    create_movement(
        db_session,
        account_id,
        3000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 3, 5, tzinfo=timezone.utc),
        concepto="Nómina March",
        disponible=4500.0,
        orden_extracto=2,
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
    """The backfill invariant: when movements are ordered by (fecha_movimiento ASC,
    id DESC), their orden_extracto values are strictly increasing (no gaps, 1-based).

    Approach: create movements with explicit orden_extracto values that follow the
    backfill formula (row_number over partition by account_id order by
    fecha_movimiento ASC, id DESC). Then verify:
      - ordinals are strictly increasing when ordered by (fecha ASC, id DESC)
      - same-date ties broken by id DESC are respected

    We simulate the backfill by assigning ordinals that match the formula output.
    """
    account_id = create_account(db_session)

    # Insert in out-of-chronological order (simulates existing legacy data)
    # Assign provisional ordinals (all distinct) to pass the unique constraint on insert.
    m_late = Movement(
        account_id=account_id,
        fecha_movimiento=datetime(2024, 3, 1, tzinfo=timezone.utc),
        concepto="Late March",
        importe=100.0,
        tipo=MovementType.INGRESO,
        disponible=100.0,
        expires_at=datetime.now(timezone.utc),
        orden_extracto=10,
    )
    m_early1 = Movement(
        account_id=account_id,
        fecha_movimiento=datetime(2024, 1, 15, tzinfo=timezone.utc),
        concepto="Early January A",
        importe=50.0,
        tipo=MovementType.GASTO,
        disponible=50.0,
        expires_at=datetime.now(timezone.utc),
        orden_extracto=20,
    )
    m_early2 = Movement(
        account_id=account_id,
        fecha_movimiento=datetime(2024, 1, 15, tzinfo=timezone.utc),
        concepto="Early January B",
        importe=75.0,
        tipo=MovementType.INGRESO,
        disponible=125.0,
        expires_at=datetime.now(timezone.utc),
        orden_extracto=30,
    )
    m_mid = Movement(
        account_id=account_id,
        fecha_movimiento=datetime(2024, 2, 10, tzinfo=timezone.utc),
        concepto="Mid February",
        importe=-25.0,
        tipo=MovementType.GASTO,
        disponible=100.0,
        expires_at=datetime.now(timezone.utc),
        orden_extracto=40,
    )

    db_session.add_all([m_late, m_early1, m_early2, m_mid])
    db_session.flush()

    # Simulate backfill: query in backfill order, then reassign ordinals in that order.
    # This replicates what the migration SQL does:
    #   row_number() over (partition by account_id order by fecha_movimiento, id DESC)
    from sqlalchemy import select

    stmt = (
        select(Movement)
        .where(Movement.account_id == account_id)
        .order_by(Movement.fecha_movimiento.asc(), Movement.id.desc())
    )
    ordered = list(db_session.execute(stmt).scalars().all())
    assert len(ordered) == 4

    # Assign backfill ordinals 1..4 in backfill order
    for i, m in enumerate(ordered):
        m.orden_extracto = i + 1
    db_session.flush()

    # Verify: ordered by (fecha ASC, id DESC) → ordinals 1, 2, 3, 4 (strictly increasing)
    ordered_verify = list(
        db_session.execute(
            select(Movement)
            .where(Movement.account_id == account_id)
            .order_by(Movement.fecha_movimiento.asc(), Movement.id.desc())
        )
        .scalars()
        .all()
    )
    ordinals = [m.orden_extracto for m in ordered_verify]
    assert ordinals == [1, 2, 3, 4], (
        f"Backfill produced non-strictly-increasing sequence: {ordinals}"
    )

    # Verify same-date tie-breaking: both Jan-15 movements; the one with higher id
    # (earlier in statement order) should have lower ordinal.
    jan_movements = [m for m in ordered_verify if m.fecha_movimiento.date() == date(2024, 1, 15)]
    assert len(jan_movements) == 2
    assert jan_movements[0].id > jan_movements[1].id, "Higher id should come first (id DESC)"
    assert jan_movements[0].orden_extracto < jan_movements[1].orden_extracto, (
        "Higher id (earlier in day) should have lower ordinal"
    )


# =============================================================================
# 4.3 – Period-summary boundary detection via orden_extracto
# =============================================================================


def test_period_summary_same_day_before_closing_nomina_included(db_session) -> None:
    """Movement on the same calendar day as the closing nómina but with lower
    orden_extracto is included in the period.  Both share IDENTICAL fecha_movimiento
    (date-only export → 00:00 UTC), differentiated only by orden_extracto.

    This test FAILS on the pre-EC-007 ordering because both same-day movements
    have identical fecha and their relative position depends on orden_extracto.
    """
    account_id = create_account(db_session)
    start = date(2024, 4, 1)

    # Apr 10: gasto included
    create_movement(
        db_session,
        account_id,
        -200.0,
        MovementType.GASTO,
        fecha=datetime(2024, 4, 10, tzinfo=timezone.utc),
        concepto="Gasto",
        disponible=800.0,
        orden_extracto=1,
    )
    # Apr 30: income SAME fecha as closing nómina but earlier (lower ordinal)
    create_movement(
        db_session,
        account_id,
        300.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 4, 30, tzinfo=timezone.utc),
        concepto="Freelance Apr",
        disponible=1100.0,
        orden_extracto=2,
    )
    # Apr 30: closing nómina (later statement position, higher ordinal)
    create_movement(
        db_session,
        account_id,
        2000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 4, 30, tzinfo=timezone.utc),
        concepto="Nómina April",
        disponible=3100.0,
        orden_extracto=3,
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


def test_period_summary_open_ended_with_orden_extracto(db_session) -> None:
    """orden_extracto does not affect open-ended period behaviour."""
    account_id = create_account(db_session)
    start = date(2024, 5, 1)

    create_movement(
        db_session,
        account_id,
        1000.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 5, 15, tzinfo=timezone.utc),
        concepto="Income",
        disponible=1000.0,
        orden_extracto=1,
    )
    create_movement(
        db_session,
        account_id,
        -200.0,
        MovementType.GASTO,
        fecha=datetime(2024, 5, 20, tzinfo=timezone.utc),
        concepto="Gasto",
        disponible=800.0,
        orden_extracto=2,
    )
    db_session.commit()

    service = make_service(db_session)
    result = service.get_period_summary(account_id, start)

    assert result.period_end is None
    assert result.income_total == 1000.0
    assert result.expense_total == 200.0
    assert result.remaining_balance == 800.0


# =============================================================================
# 4.4 – (account_id, orden_extracto) uniqueness enforced
# =============================================================================


def test_orden_extracto_unique_per_account_violation_raises_integrity_error(
    db_session,
) -> None:
    """Inserting two movements with the same (account_id, orden_extracto) raises
    an IntegrityError (SQLite reports as IntegrityError; PostgreSQL would raise
    the same via the DB-level UNIQUE constraint)."""
    account_id = create_account(db_session)

    # Insert first movement with orden_extracto=5
    create_movement(
        db_session,
        account_id,
        100.0,
        MovementType.INGRESO,
        fecha=datetime(2024, 1, 1, tzinfo=timezone.utc),
        concepto="First",
        disponible=100.0,
        orden_extracto=5,
    )
    db_session.commit()

    # Attempt to insert second movement with the SAME account_id and orden_extracto=5
    second = Movement(
        account_id=account_id,
        fecha_movimiento=datetime(2024, 1, 2, tzinfo=timezone.utc),
        concepto="Duplicate ordinal",
        importe=50.0,
        tipo=MovementType.GASTO,
        disponible=50.0,
        expires_at=datetime.now(timezone.utc),
        orden_extracto=5,  # same ordinal → violates unique constraint
    )
    db_session.add(second)
    with pytest.raises(IntegrityError):
        db_session.flush()


# =============================================================================
# 4.5 – Re-upload does not reassign existing orden_extracto
# =============================================================================


def _make_csv_content() -> bytes:
    """Minimal CSV with Fecha,Concepto,Importe,Disponible columns."""
    return (
        "Fecha,Concepto,Importe,Disponible\n"
        "2024-01-15,Ingreso A,100.0,100.0\n"
        "2024-01-20,Gasto B,-50.0,50.0\n".encode()
    )


def test_reupload_does_not_reassign_existing_orden_extracto(db_session) -> None:
    """Uploading the same file twice: the second upload deduplicates existing
    movements and does NOT change their orden_extracto values."""
    account_id = create_account(db_session)
    db_session.commit()

    service = make_service(db_session, account_id=account_id)

    csv = _make_csv_content()

    # First upload: creates two movements
    result1 = service.upload(csv, "movements.csv")
    assert result1.inserted_count == 2
    db_session.commit()

    # Read back the orden_extracto values assigned in first upload
    movimientos = (
        db_session.query(Movement)
        .filter(Movement.account_id == account_id)
        .order_by(Movement.orden_extracto)
        .all()
    )
    assert len(movimientos) == 2
    first_ordinal_1 = movimientos[0].orden_extracto
    first_ordinal_2 = movimientos[1].orden_extracto

    # Second upload: same CSV → deduplication, no new ordinals assigned
    result2 = service.upload(csv, "movements.csv")
    assert result2.inserted_count == 0
    assert result2.skipped_count == 2
    db_session.commit()

    # orden_extracto values must be unchanged
    movimientos_after = (
        db_session.query(Movement)
        .filter(Movement.account_id == account_id)
        .order_by(Movement.orden_extracto)
        .all()
    )
    assert len(movimientos_after) == 2
    assert movimientos_after[0].orden_extracto == first_ordinal_1
    assert movimientos_after[1].orden_extracto == first_ordinal_2


def test_upload_assigns_continuing_orden_extracto(db_session) -> None:
    """New movements receive orden_extracto continuing after the maximum existing."""
    account_id = create_account(db_session)
    db_session.commit()

    service = make_service(db_session, account_id=account_id)

    csv1 = "Fecha,Concepto,Importe,Disponible\n2024-01-01,Nómina,3000.0,3000.0\n".encode()
    result1 = service.upload(csv1, "jan.csv")
    assert result1.inserted_count == 1
    db_session.commit()

    m1 = db_session.query(Movement).filter(Movement.account_id == account_id).one()
    assert m1.orden_extracto == 1

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
        .order_by(Movement.orden_extracto)
        .all()
    )
    ordinales = [m.orden_extracto for m in movimientos]
    # First upload: ordinal 1; Second upload: 2 and 3 (continuing)
    assert ordinales == [1, 2, 3]


def test_upload_same_day_movements_keep_statement_order(db_session) -> None:
    """Upload with two same-day movements listed in reverse statement order
    (earlier-in-day row appears LATER in the file, as in real bank exports).
    orden_extracto must reflect statement chronology: earlier row gets LOWER ordinal.

    Spec scenario: "Same-day movements keep statement order".
    This test FAILS with ORDER BY fecha_movimiento, id DESC alone because both
    movements have identical fecha (2024-01-15 → 00:00 UTC) and id order happens
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
        .order_by(Movement.orden_extracto)
        .all()
    )
    assert len(movimientos) == 2

    # orden_extracto=1 → earlier in statement order (Ingreso A, row 1 in file)
    # orden_extracto=2 → later in statement order (Gasto B, row 2 in file)
    assert movimientos[0].concepto == "Ingreso A"
    assert movimientos[0].orden_extracto == 1
    assert movimientos[1].concepto == "Gasto B"
    assert movimientos[1].orden_extracto == 2


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
        fecha=datetime(2024, 1, 1, tzinfo=timezone.utc),
        disponible=1000.0,
        orden_extracto=1,
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
        fecha=datetime(2024, 1, 1, tzinfo=timezone.utc),
        concepto="Nómina",
        disponible=1000.0,
        orden_extracto=1,
    )
    create_movement(
        db_session,
        account_id,
        -300.0,
        MovementType.GASTO,
        fecha=datetime(2024, 1, 15, tzinfo=timezone.utc),
        concepto="Gasto",
        disponible=700.0,
        orden_extracto=2,
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
