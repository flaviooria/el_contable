"""create accounts and piggy_banks tables

Revision ID: b7303b461e7f
Revises: 725bfc1ff628
Create Date: 2026-08-28 15:47:01.249329

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7303b461e7f"
down_revision: Union[str, Sequence[str], None] = "725bfc1ff628"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("account_balances")

    op.create_table(
        "accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("saldo_base", sa.Float(), nullable=False),
        sa.Column("fecha_ingreso", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    default_account_id = sa.text("'00000000-0000-0000-0000-000000000001'::uuid")
    op.execute(
        f"INSERT INTO accounts (id, saldo_base, fecha_ingreso, created_at) VALUES ({default_account_id}, 0.0, NOW(), NOW())"
    )

    op.create_table(
        "piggy_banks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("saldo_maximo", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre", "account_id", name="uq_piggy_bank_nombre_account"),
    )
    op.create_table(
        "movements_piggy_banks",
        sa.Column("movement_id", sa.Integer(), nullable=False),
        sa.Column("piggy_bank_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["movement_id"],
            ["movements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["piggy_bank_id"],
            ["piggy_banks.id"],
        ),
        sa.PrimaryKeyConstraint("movement_id", "piggy_bank_id"),
    )

    op.add_column("movements", sa.Column("account_id", sa.UUID(), nullable=True))
    op.execute(
        "UPDATE movements SET account_id = '00000000-0000-0000-0000-000000000001'::uuid WHERE account_id IS NULL"
    )
    op.alter_column("movements", "account_id", nullable=False)
    op.create_foreign_key(None, "movements", "accounts", ["account_id"], ["id"])

    op.create_table(
        "account_balances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("account_balances")
    op.drop_constraint(None, "movements", type_="foreignkey")
    op.execute("UPDATE movements SET account_id = NULL")
    op.drop_column("movements", "account_id")
    op.drop_table("movements_piggy_banks")
    op.drop_table("piggy_banks")
    op.execute("DELETE FROM accounts WHERE id = '00000000-0000-0000-0000-000000000001'::uuid")
    op.drop_table("accounts")

    op.create_table(
        "account_balances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
