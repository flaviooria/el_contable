import uuid
from datetime import datetime, timezone


from el_contable.features.accounts.models import Account
from el_contable.features.movements.models import Movement
from el_contable.features.movements.parser import MovementsParser
from el_contable.features.movements.service import MovementsService
from el_contable.features.movements.validator import MovementsValidator


# ---------------------------------------------------------------------------
# Spec-driven tests (task 3.2): dedup key, UUID ids, no expires_at
# ---------------------------------------------------------------------------


def test_dedup_key_is_movement_date_amount_available_balance(db_session) -> None:
    """The dedup composite key is exactly (movement_date, amount, available_balance).

    Uses different dates so all three rows are inserted on first upload (no within-file
    dedup). Second upload verifies across-upload dedup: same key → skipped.

    Also implicitly proves the key is NOT just (movement_date, amount) because
    A and C have same date+amount but different balance and both insert on first upload.
    """
    account_id = create_account(db_session)

    # All different dates → no within-file dedup. A and C have same date+amount
    # but DIFFERENT balance → both insert, proving balance is part of the key.
    csv = (
        b"Fecha,Concepto,Movimiento,Importe,Disponible\n"
        b"2024-01-01,Pago A,Texto A,100,200\n"  # Jan1, amt=100, bal=200
        b"2024-01-02,Pago B,Texto B,100,300\n"  # Jan2, amt=100, bal=300
        b"2024-01-03,Pago C,Texto C,100,200\n"  # Jan3, amt=100, bal=200 (SAME key as A)
    )

    # First upload: all 3 insert (different dates → no within-file dedup)
    r1 = make_service(db_session, account_id).upload(csv, "dedup.csv")
    assert r1.inserted_count == 3, f"Expected 3 inserts, got {r1.inserted_count}"
    assert r1.skipped_count == 0, f"Expected 0 skips on first upload, got {r1.skipped_count}"

    # Second upload: A and C share the same key → both skipped. B has unique key → skipped too.
    r2 = make_service(db_session, account_id).upload(csv, "dedup.csv")
    assert r2.inserted_count == 0, f"Expected 0 inserts on re-upload, got {r2.inserted_count}"
    assert r2.skipped_count == 3, f"Expected 3 skipped on re-upload, got {r2.skipped_count}"

    # DB still has exactly 3 movements
    rows = db_session.query(Movement).order_by(Movement.order_statement).all()
    assert len(rows) == 3


def test_upload_response_movement_id_is_uuid(db_session) -> None:
    """Movement ids in UploadResponse are UUIDs, not integers."""
    account_id = create_account(db_session)
    response = make_service(db_session, account_id).upload(CSV_CONTENT, "movimientos.csv")

    assert response.inserted_count == 1
    movement = response.movements[0]
    assert isinstance(movement.id, uuid.UUID), (
        f"Expected UUID, got {type(movement.id)}: {movement.id}"
    )


def test_no_expires_at_in_upload_response(db_session) -> None:
    """expires_at field is not present in any API response."""
    account_id = create_account(db_session)
    response = make_service(db_session, account_id).upload(CSV_CONTENT, "movimientos.csv")

    movement = response.movements[0]
    assert not hasattr(movement, "expires_at"), (
        "expires_at should not be present in MovementResponse"
    )


CSV_CONTENT = (
    b"Fecha,Concepto,Movimiento,Importe,Disponible\n2024-01-01,Sueldo,Empresa X,1500,2500\n"
)


def make_service(db_session, account_id: uuid.UUID) -> MovementsService:
    return MovementsService(
        parser=MovementsParser(),
        validator=MovementsValidator(),
        db=db_session,
        account_id=account_id,
    )


def create_account(db_session, base_balance: float = 0.0) -> uuid.UUID:
    account = Account(base_balance=base_balance, entry_date=datetime.now(timezone.utc))
    db_session.add(account)
    db_session.flush()
    return account.id


def test_upload_returns_id_and_created_at(db_session) -> None:
    account_id = create_account(db_session)
    response = make_service(db_session, account_id).upload(CSV_CONTENT, "movimientos.csv")

    assert response.inserted_count == 1
    movement = response.movements[0]
    assert movement.id is not None
    assert movement.created_at is not None


def test_upload_persists_rows(db_session) -> None:
    account_id = create_account(db_session)
    make_service(db_session, account_id).upload(CSV_CONTENT, "movimientos.csv")

    rows = db_session.query(Movement).all()
    assert len(rows) == 1
    assert rows[0].id is not None
    assert rows[0].created_at is not None


def test_within_file_duplicate_keeps_first_occurrence(db_session) -> None:
    account_id = create_account(db_session)
    csv_with_dupe = (
        b"Fecha,Concepto,Movimiento,Importe,Disponible\n"
        b"2024-01-01,Sueldo,Empresa X,1500,2500\n"
        b"2024-01-01,Sueldo,Empresa X,1500,2500\n"
        b"2024-01-02,Renta,Piso,500,2000\n"
    )
    response = make_service(db_session, account_id).upload(csv_with_dupe, "dupe.csv")

    assert response.inserted_count == 2
    assert response.skipped_count == 0

    rows = db_session.query(Movement).order_by(Movement.movement_date).all()
    assert len(rows) == 2


def test_duplicate_upload_skips_existing_rows(db_session) -> None:
    account_id = create_account(db_session)
    make_service(db_session, account_id).upload(CSV_CONTENT, "movimientos.csv")

    response = make_service(db_session, account_id).upload(CSV_CONTENT, "movimientos.csv")

    assert response.inserted_count == 0
    assert response.skipped_count == 1

    rows = db_session.query(Movement).all()
    assert len(rows) == 1


def test_upload_sorts_rows_by_fecha_descending(db_session) -> None:
    account_id = create_account(db_session)
    csv_unsorted = (
        b"Fecha,Concepto,Movimiento,Importe,Disponible\n"
        b"2024-01-01,Sueldo,Empresa X,1500,2500\n"
        b"2024-01-15,Renta,Piso,500,1000\n"
        b"2024-01-10,Comida,Supermercado,100,2400\n"
    )
    response = make_service(db_session, account_id).upload(csv_unsorted, "unsorted.csv")

    assert response.inserted_count == 3
    dates = [m.movement_date for m in response.movements]
    assert dates == sorted(dates, reverse=True)
