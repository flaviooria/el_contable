from datetime import date, datetime

import polars as pl
from polars import DataFrame

from el_contable.features.movements.schemas import MovementRow

REQUIRED_COLUMNS = ["Fecha", "Concepto", "Importe", "Disponible"]
OPTIONAL_COLUMNS = ["Movimiento"]


class ParserError(Exception):
    def __init__(self, message: str, details: list[str] | None = None):
        self.message = message
        self.details = details or []
        super().__init__(self.message)


class MovementsParser:
    def parse(self, file_content: bytes, filename: str) -> list[MovementRow]:
        extension = filename.split(".")[-1].lower()

        if extension == "csv":
            df = pl.read_csv(file_content)
        elif extension in ("xlsx", "xls"):
            df = pl.read_excel(file_content)
        else:
            raise ParserError(f"Unsupported file type: {extension}")

        return self._process_dataframe(df)

    def _process_dataframe(self, df: DataFrame) -> list[MovementRow]:
        df = df.rename({col: col.strip() for col in df.columns})

        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            raise ParserError(
                f"Missing required columns: {', '.join(missing_columns)}",
                details=missing_columns,
            )

        rows: list[MovementRow] = []
        for row in df.iter_rows(named=True):
            movement_row = self._parse_row(row)
            rows.append(movement_row)

        return rows

    def _parse_row(self, row: dict) -> MovementRow:
        fecha = row.get("Fecha")
        concept_raw = row.get("Concepto")
        movimiento = row.get("Movimiento")
        amount_raw = row.get("Importe")
        available_raw = row.get("Disponible")

        raw_fecha = self._as_string(fecha)

        parsed_row = MovementRow(
            fecha=raw_fecha,
            concept=concept_raw,
            movimiento=movimiento,
            amount=amount_raw,
            available_balance=available_raw,
            is_valid=True,
            validation_error=None,
        )

        if raw_fecha is None or not raw_fecha.strip():
            parsed_row.is_valid = False
            parsed_row.validation_error = "Fecha is required"
            return parsed_row

        try:
            parsed_row.movement_date = self._parse_date(raw_fecha)
        except ValueError:
            parsed_row.is_valid = False
            parsed_row.validation_error = f"Invalid date format: {raw_fecha}"
            return parsed_row

        if concept_raw is None or (isinstance(concept_raw, str) and not concept_raw.strip()):
            parsed_row.is_valid = False
            parsed_row.validation_error = "Concepto is required"
            return parsed_row

        if amount_raw is None:
            parsed_row.is_valid = False
            parsed_row.validation_error = "Importe is required"
            return parsed_row

        try:
            parsed_row.amount = float(amount_raw)
        except (ValueError, TypeError):
            parsed_row.is_valid = False
            parsed_row.validation_error = f"Invalid Importe: {amount_raw}"
            return parsed_row

        if available_raw is not None:
            try:
                parsed_row.available_balance = float(available_raw)
            except (ValueError, TypeError):
                parsed_row.is_valid = False
                parsed_row.validation_error = f"Invalid Disponible: {available_raw}"
                return parsed_row

        return parsed_row

    def _as_string(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _parse_date(self, date_str: str) -> date:
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]
        date_str = date_str.strip()
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.date()
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {date_str}")
