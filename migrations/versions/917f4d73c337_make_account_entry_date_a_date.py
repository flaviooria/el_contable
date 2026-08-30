"""make account entry_date a date

Revision ID: 917f4d73c337
Revises: dfea6d2fbc87
Create Date: 2026-08-30 18:39:12.101769

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "917f4d73c337"
down_revision: Union[str, Sequence[str], None] = "dfea6d2fbc87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "accounts",
        "entry_date",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.Date(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "accounts",
        "entry_date",
        existing_type=sa.Date(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
