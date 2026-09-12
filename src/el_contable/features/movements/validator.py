from el_contable.features.movements.schemas import MovementRow


class MovementValidationError(Exception):
    pass


class MovementsValidator:
    @staticmethod
    def combine_concept(row: MovementRow) -> str:
        """Join the payment type and the detail into a single concept string.

        Returns ``Concepto`` alone when ``Movimiento`` is empty.
        """
        concept = row.concept or ""
        concept = concept.strip()

        if row.movimiento and row.movimiento.strip():
            return f"{concept} - {row.movimiento.strip()}"

        return concept

    @staticmethod
    def determine_movement_type(amount: float) -> str:
        """Return ``ingreso`` for non-negative amounts, ``gasto`` otherwise."""
        return "ingreso" if amount >= 0 else "gasto"
