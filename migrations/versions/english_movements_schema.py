"""english movements schema (uuid pk, date, drop expires_at, english columns)

Revision ID: english_movements_schema
Revises: a1b2c3d4e5f6
Create Date: 2026-09-12 00:00:00.000000

Sequence (PG-safe):
  1. Add nullable id_uuid UUID to movements; backfill gen_random_uuid().
  2. Add nullable movement_id_uuid UUID to movements_piggy_banks; backfill by joining old id.
  3. Drop FK and legacy PK/columns on movements_piggy_banks.
  4. Rename remaining movements columns, alter movement_date to Date, drop expires_at,
     drop old id, promote id_uuid to non-null PK id.
  5. Recreate movements_piggy_banks PK + FK to new UUID movements.id.
  6. Rename unique constraint to uq_movements_account_order_statement.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "english_movements_schema"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: UUID PK, Date movement_date, English columns, drop expires_at."""
    # 1. Add nullable UUID id column; backfill with gen_random_uuid()
    op.add_column(
        "movements",
        sa.Column("id_uuid", sa.UUID(), nullable=True),
    )
    op.execute(text("UPDATE movements SET id_uuid = gen_random_uuid()"))
    op.alter_column("movements", "id_uuid", nullable=False)

    # 2. Add nullable UUID movement_id_uuid to movements_piggy_banks; backfill by joining old id
    op.add_column(
        "movements_piggy_banks",
        sa.Column("movement_id_uuid", sa.UUID(), nullable=True),
    )
    op.execute(
        text(
            "UPDATE movements_piggy_banks "
            "SET movement_id_uuid = (SELECT id_uuid FROM movements m WHERE m.id = movements_piggy_banks.movement_id)"
        ),
    )
    op.alter_column("movements_piggy_banks", "movement_id_uuid", nullable=False)

    # 3. Drop FK and legacy PK/columns on movements_piggy_banks
    op.drop_constraint("movements_piggy_banks_pkey", "movements_piggy_banks", type_="primary")
    op.drop_column("movements_piggy_banks", "movement_id")
    op.alter_column(
        "movements_piggy_banks",
        "movement_id_uuid",
        new_column_name="movement_id",
    )

    # 4. Rename movements columns, alter movement_date to Date, drop expires_at,
    #    drop old id, promote id_uuid to non-null PK id
    op.alter_column("movements", "fecha_movimiento", new_column_name="movement_date")
    op.alter_column("movements", "concepto", new_column_name="concept")
    op.alter_column("movements", "importe", new_column_name="amount")
    op.alter_column("movements", "tipo", new_column_name="type")
    op.alter_column("movements", "disponible", new_column_name="available_balance")
    op.alter_column("movements", "orden_extracto", new_column_name="order_statement")
    op.drop_column("movements", "expires_at")
    op.drop_column("movements", "id")
    op.alter_column("movements", "id_uuid", new_column_name="id")
    # Alter movement_date from DateTime to Date
    op.alter_column(
        "movements",
        "movement_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=False,
    )

    # Promote UUID id to primary key
    op.create_primary_key("movements_pkey", "movements", ["id"])

    # 5. Recreate movements_piggy_banks PK + FK to new UUID movements.id
    op.create_primary_key(
        "movements_piggy_banks_pkey",
        "movements_piggy_banks",
        ["movement_id", "piggy_bank_id"],
    )
    op.create_foreign_key(
        None,
        "movements_piggy_banks",
        "movements",
        ["movement_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 6. Rename unique constraint to uq_movements_account_order_statement
    op.drop_constraint(
        "uq_movements_account_orden",
        "movements",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_movements_account_order_statement",
        "movements",
        ["account_id", "order_statement"],
    )


def downgrade() -> None:
    """Downgrade schema: back to bigint sequential PK, DateTime movement_date, Spanish columns, add expires_at."""
    # Drop FK and PK on movements_piggy_banks
    op.drop_constraint(
        "movements_piggy_banks_movement_id_fkey",
        "movements_piggy_banks",
        type_="foreignkey",
    )
    op.drop_constraint(
        "movements_piggy_banks_pkey",
        "movements_piggy_banks",
        type_="primary",
    )

    # Drop the English unique constraint (not needed in downgrade)
    op.drop_constraint(
        "uq_movements_account_order_statement",
        "movements",
        type_="unique",
    )

    # Add both integer backup columns BEFORE any demotion so joins stay UUID=UUID
    op.add_column(
        "movements",
        sa.Column("id_old", sa.Integer(), nullable=True),
    )
    op.add_column(
        "movements_piggy_banks",
        sa.Column("movement_id_old", sa.Integer(), nullable=True),
    )

    # Backfill movements.id_old with sequential ints (uuid=uuid join, still valid here)
    op.execute(
        text(
            "WITH numbered AS ("
            "  SELECT id, row_number() OVER (PARTITION BY account_id ORDER BY order_statement) AS new_id "
            "  FROM movements"
            ")"
            "UPDATE movements m SET id_old = numbered.new_id FROM numbered WHERE m.id = numbered.id"
        ),
    )

    # Backfill movements_piggy_banks.movement_id_old via uuid=uuid join
    # movements.id is still UUID at this point
    op.execute(
        text(
            "UPDATE movements_piggy_banks mpb "
            "SET movement_id_old = ("
            "  SELECT m.id_old::integer "
            "  FROM movements m "
            "  WHERE m.id = mpb.movement_id"
            ")"
        ),
    )

    # Now demote: make cols non-null, drop UUID cols, rename to final names
    op.alter_column("movements", "id_old", nullable=False)
    op.alter_column("movements_piggy_banks", "movement_id_old", nullable=False)

    op.drop_column("movements", "id")
    op.alter_column("movements", "id_old", new_column_name="id")
    op.drop_column("movements_piggy_banks", "movement_id")
    op.alter_column("movements_piggy_banks", "movement_id_old", new_column_name="movement_id")

    # Recreate movements PK (required before FK can reference it)
    op.create_primary_key("movements_pkey", "movements", ["id"])

    # Add back expires_at
    op.add_column(
        "movements",
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Convert movement_date back to DateTime (rename column back at the same time)
    op.alter_column(
        "movements",
        "movement_date",
        new_column_name="fecha_movimiento",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    # Rename remaining English columns back to Spanish
    op.alter_column("movements", "concept", new_column_name="concepto")
    op.alter_column("movements", "amount", new_column_name="importe")
    op.alter_column("movements", "type", new_column_name="tipo")
    op.alter_column("movements", "available_balance", new_column_name="disponible")
    op.alter_column("movements", "order_statement", new_column_name="orden_extracto")

    # Create unique constraint with Spanish column name (after columns are renamed)
    op.create_unique_constraint(
        "uq_movements_account_orden",
        "movements",
        ["account_id", "orden_extracto"],
    )

    op.create_primary_key(
        "movements_piggy_banks_pkey",
        "movements_piggy_banks",
        ["movement_id", "piggy_bank_id"],
    )
    op.create_foreign_key(
        None,
        "movements_piggy_banks",
        "movements",
        ["movement_id"],
        ["id"],
        ondelete="CASCADE",
    )
