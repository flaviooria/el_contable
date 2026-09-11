"""add orden_extracto to movements

Revision ID: a1b2c3d4e5f6
Revises: 917f4d73c337
Create Date: 2026-09-11 23:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "917f4d73c337"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable orden_extracto, backfill with row_number, set NOT NULL, add unique constraint."""
    # 1. Add nullable column
    op.add_column("movements", sa.Column("orden_extracto", sa.Integer(), nullable=True))

    # 2. Backfill using a CTE with row_number window function
    backfill_sql = text(
        """
        WITH ordered AS (
            SELECT id, row_number() OVER (PARTITION BY account_id ORDER BY fecha_movimiento, id DESC) AS rn
            FROM movements
        )
        UPDATE movements m
        SET orden_extracto = ordered.rn
        FROM ordered
        WHERE m.id = ordered.id
        """
    )
    op.execute(backfill_sql)

    # 3. Set NOT NULL
    op.alter_column("movements", "orden_extracto", nullable=False)

    # 4. Add unique constraint
    op.create_unique_constraint(
        "uq_movements_account_orden",
        "movements",
        ["account_id", "orden_extracto"],
    )


def downgrade() -> None:
    """Drop unique constraint and orden_extracto column."""
    op.drop_constraint("uq_movements_account_orden", "movements", type_="unique")
    op.drop_column("movements", "orden_extracto")
