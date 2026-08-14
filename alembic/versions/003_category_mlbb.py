"""Add MLBB article category

Revision ID: 003_category_mlbb
Revises: 002_mlbb_example
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_category_mlbb"
down_revision: Union[str, None] = "002_mlbb_example"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO categories (slug, name_ru, name_en)
            SELECT 'mlbb', 'MLBB', 'MLBB'
            WHERE NOT EXISTS (SELECT 1 FROM categories WHERE slug = 'mlbb')
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM categories WHERE slug = 'mlbb'"))
