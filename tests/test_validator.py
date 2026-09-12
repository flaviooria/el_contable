from datetime import date

from el_contable.features.movements.schemas import MovementRow
from el_contable.features.movements.validator import MovementsValidator


def make_row(**overrides) -> MovementRow:
    defaults = {
        "movement_date": date(2024, 1, 2),
        "concept": "Renta",
        "movimiento": None,
        "amount": -50.0,
        "available_balance": 2450.0,
        "is_valid": True,
        "validation_error": None,
    }
    defaults.update(overrides)
    return MovementRow(**defaults)


def test_combine_concept_with_movimiento() -> None:
    validator = MovementsValidator()

    assert validator.combine_concept(make_row(movimiento="Pago mensual")) == "Renta - Pago mensual"
    assert validator.combine_concept(make_row(movimiento="")) == "Renta"


def test_determine_movement_type() -> None:
    validator = MovementsValidator()

    assert validator.determine_movement_type(1500.0) == "ingreso"
    assert validator.determine_movement_type(-50.0) == "gasto"
