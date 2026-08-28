import polars as pl

from el_contable.features.movements.parser import MovementsParser, ParserError

CSV_CONTENT = b"Fecha,Concepto,Movimiento,Importe,Disponible\n2024-01-01,Sueldo,Empresa X,1500,2500\n2024-01-02,Renta,, -50,2450\n"


def test_parse_valid_csv() -> None:
    rows = MovementsParser().parse(CSV_CONTENT, "movimientos.csv")

    assert len(rows) == 2
    assert rows[0].is_valid
    assert rows[0].fecha == "2024-01-01"
    assert rows[0].fecha_movimiento is not None
    assert rows[0].importe == 1500.0
    assert rows[1].is_valid
    assert rows[1].importe == -50.0


def test_parse_missing_fecha_marks_invalid() -> None:
    content = b"Fecha,Concepto,Importe,Disponible\n,Sueldo,100,100\n"
    rows = MovementsParser().parse(content, "movimientos.csv")

    assert len(rows) == 1
    assert rows[0].is_valid is False
    assert rows[0].validation_error == "Fecha is required"


def test_parse_unsupported_extension_raises() -> None:
    parser = MovementsParser()
    try:
        parser.parse(b"", "movimientos.txt")
    except ParserError as exc:
        assert "Unsupported file type" in str(exc)
    else:
        raise AssertionError("Expected ParserError to be raised")


def test_parse_missing_required_column_raises() -> None:
    content = b"Fecha,Concepto,Importe\n2024-01-01,Sueldo,100\n"
    try:
        MovementsParser().parse(content, "movimientos.csv")
    except ParserError as exc:
        assert "Missing required columns" in str(exc)
    else:
        raise AssertionError("Expected ParserError to be raised")


def test_parse_date_with_timezone() -> None:
    rows = pl.read_csv(b"Fecha,Concepto,Importe,Disponible\n2024-01-01,Sueldo,100,100\n")

    parsed_rows = MovementsParser()._process_dataframe(rows)
    assert parsed_rows[0].fecha == "2024-01-01"
    assert parsed_rows[0].fecha_movimiento is not None
    assert parsed_rows[0].fecha_movimiento.tzinfo is not None
