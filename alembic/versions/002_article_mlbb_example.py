"""Add mlbb_example to article_translations

Revision ID: 002_mlbb_example
Revises: 002_day4_auth_profiles
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_mlbb_example"
down_revision: Union[str, None] = "002_day4_auth_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "article_translations",
        sa.Column("mlbb_example", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("article_translations", "mlbb_example", server_default=None)


def downgrade() -> None:
    op.drop_column("article_translations", "mlbb_example")
