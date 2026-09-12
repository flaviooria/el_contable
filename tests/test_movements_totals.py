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
    order_statement: int = 1,
) -> Movement:
    movement = Movement(
        account_id=account_id,
        movement_date=movement_date or datetime.now(timezone.utc).date(),
        concept="Test movement",
        amount=amount,
        type=movement_type,
        available_balance=amount,
        order_statement=order_statement,
    )
    db_session.add(movement)
    db_session.flush()
    return movement


def test_get_totals_returns_correct_sums_for_both_types(db_session) -> None:
    account_id = create_account(db_session)
    create_movement(db_session, account_id, 1000.0, MovementType.INGRESO, order_statement=1)
    create_movement(db_session, account_id, 500.0, MovementType.INGRESO, order_statement=2)
    create_movement(db_session, account_id, 200.0, MovementType.GASTO, order_statement=3)
    create_movement(db_session, account_id, 50.0, MovementType.GASTO, order_statement=4)
    db_session.commit()

    service = make_service(db_session)
    result = service.get_totals(account_id)

    assert result.account_id == account_id
    assert len(result.totals) == 2

    ingreso_total = next(t for t in result.totals if t.type == MovementType.INGRESO)
    gasto_total = next(t for t in result.totals if t.type == MovementType.GASTO)

    assert ingreso_total.total_amount == 1500.0
    assert ingreso_total.count == 2
    assert gasto_total.total_amount == 250.0
    assert gasto_total.count == 2


def test_get_totals_returns_zero_totals_when_no_movements(db_session) -> None:
    account_id = create_account(db_session)
    db_session.commit()

    service = make_service(db_session)
    result = service.get_totals(account_id)

    assert result.account_id == account_id
    assert len(result.totals) == 2

    ingreso_total = next(t for t in result.totals if t.type == MovementType.INGRESO)
    gasto_total = next(t for t in result.totals if t.type == MovementType.GASTO)

    assert ingreso_total.total_amount == 0.0
    assert ingreso_total.count == 0
    assert gasto_total.total_amount == 0.0
    assert gasto_total.count == 0


def test_get_totals_raises_error_for_nonexistent_account(db_session) -> None:
    nonexistent_id = uuid.uuid4()
    service = make_service(db_session)

    with pytest.raises(ValueError, match="Account not found"):
        service.get_totals(nonexistent_id)


def test_get_totals_returns_only_ingreso_when_no_gastos(db_session) -> None:
    account_id = create_account(db_session)
    create_movement(db_session, account_id, 1000.0, MovementType.INGRESO, order_statement=1)
    create_movement(db_session, account_id, 500.0, MovementType.INGRESO, order_statement=2)
    db_session.commit()

    service = make_service(db_session)
    result = service.get_totals(account_id)

    assert len(result.totals) == 2

    ingreso_total = next(t for t in result.totals if t.type == MovementType.INGRESO)
    gasto_total = next(t for t in result.totals if t.type == MovementType.GASTO)

    assert ingreso_total.total_amount == 1500.0
    assert ingreso_total.count == 2
    assert gasto_total.total_amount == 0.0
    assert gasto_total.count == 0


def test_get_totals_returns_only_gasto_when_no_ingresos(db_session) -> None:
    account_id = create_account(db_session)
    create_movement(db_session, account_id, 200.0, MovementType.GASTO, order_statement=1)
    create_movement(db_session, account_id, 50.0, MovementType.GASTO, order_statement=2)
    db_session.commit()

    service = make_service(db_session)
    result = service.get_totals(account_id)

    assert len(result.totals) == 2

    ingreso_total = next(t for t in result.totals if t.type == MovementType.INGRESO)
    gasto_total = next(t for t in result.totals if t.type == MovementType.GASTO)

    assert ingreso_total.total_amount == 0.0
    assert ingreso_total.count == 0
    assert gasto_total.total_amount == 250.0
    assert gasto_total.count == 2


# =============================================================================
# HTTP contract tests (TestClient / integration tests)
# =============================================================================


def test_get_totals_returns_404_for_nonexistent_account(client) -> None:
    """GET /api/v1/movements/totals?account_id=<nonexistent> returns HTTP 404."""
    nonexistent_id = uuid.uuid4()
    response = client.get(f"/api/v1/movements/totals?account_id={nonexistent_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Account not found"}


def test_get_totals_returns_422_when_account_id_missing(client) -> None:
    """GET /api/v1/movements/totals (no account_id) returns HTTP 422."""
    response = client.get("/api/v1/movements/totals")

    assert response.status_code == 422
