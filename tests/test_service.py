import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from el_contable.features.account_balance.models import Base as AccountBalanceBase
from el_contable.features.movements.models import Base, Movement
from el_contable.features.movements.parser import MovementsParser
from el_contable.features.movements.service import MovementsService
from el_contable.features.movements.validator import MovementsValidator

CSV_CONTENT = (
    b"Fecha,Concepto,Movimiento,Importe,Disponible\n2024-01-01,Sueldo,Empresa X,1500,2500\n"
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    AccountBalanceBase.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def make_service(db_session) -> MovementsService:
    return MovementsService(
        parser=MovementsParser(),
        validator=MovementsValidator(),
        db=db_session,
    )


def test_upload_returns_id_and_created_at(db_session) -> None:
    response = make_service(db_session).upload(CSV_CONTENT, "movimientos.csv")

    assert response.inserted_count == 1
    movement = response.movements[0]
    assert movement.id is not None
    assert movement.created_at is not None
    assert movement.expires_at is not None


def test_upload_persists_rows(db_session) -> None:
    make_service(db_session).upload(CSV_CONTENT, "movimientos.csv")

    rows = db_session.query(Movement).all()
    assert len(rows) == 1
    assert rows[0].id is not None
    assert rows[0].created_at is not None


def test_within_file_duplicate_keeps_first_occurrence(db_session) -> None:
    csv_with_dupe = (
        b"Fecha,Concepto,Movimiento,Importe,Disponible\n"
        b"2024-01-01,Sueldo,Empresa X,1500,2500\n"
        b"2024-01-01,Sueldo,Empresa X,1500,2500\n"
        b"2024-01-02,Renta,Piso,500,2000\n"
    )
    response = make_service(db_session).upload(csv_with_dupe, "dupe.csv")

    assert response.inserted_count == 2
    assert response.skipped_count == 0

    rows = db_session.query(Movement).order_by(Movement.fecha_movimiento).all()
    assert len(rows) == 2


def test_duplicate_upload_skips_existing_rows(db_session) -> None:
    make_service(db_session).upload(CSV_CONTENT, "movimientos.csv")

    response = make_service(db_session).upload(CSV_CONTENT, "movimientos.csv")

    assert response.inserted_count == 0
    assert response.skipped_count == 1

    rows = db_session.query(Movement).all()
    assert len(rows) == 1


def test_upload_sorts_rows_by_fecha_descending(db_session) -> None:
    csv_unsorted = (
        b"Fecha,Concepto,Movimiento,Importe,Disponible\n"
        b"2024-01-01,Sueldo,Empresa X,1500,2500\n"
        b"2024-01-15,Renta,Piso,500,1000\n"
        b"2024-01-10,Comida,Supermercado,100,2400\n"
    )
    response = make_service(db_session).upload(csv_unsorted, "unsorted.csv")

    assert response.inserted_count == 3
    fechas = [m.fecha_movimiento for m in response.movements]
    assert fechas == sorted(fechas, reverse=True)
