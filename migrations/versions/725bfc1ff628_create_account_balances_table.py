"""create account_balances table

Revision ID: 725bfc1ff628
Revises: cb4c9d7b1cb6
Create Date: 2026-08-28 14:25:52.204894

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "725bfc1ff628"
down_revision: Union[str, Sequence[str], None] = "cb4c9d7b1cb6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "account_balances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("account_balances")
