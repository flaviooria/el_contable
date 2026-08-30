"""rename spanish columns to english

Revision ID: 4ede7a986064
Revises: b7303b461e7f
Create Date: 2026-08-28 16:16:03.839963

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4ede7a986064"
down_revision: Union[str, Sequence[str], None] = "b7303b461e7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("accounts", "saldo_base", new_column_name="base_balance")
    op.alter_column("accounts", "fecha_ingreso", new_column_name="entry_date")
    op.alter_column("piggy_banks", "nombre", new_column_name="name")
    op.alter_column("piggy_banks", "saldo_maximo", new_column_name="max_balance")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("piggy_banks", "max_balance", new_column_name="saldo_maximo")
    op.alter_column("piggy_banks", "name", new_column_name="nombre")
    op.alter_column("accounts", "entry_date", new_column_name="fecha_ingreso")
    op.alter_column("accounts", "base_balance", new_column_name="saldo_base")
