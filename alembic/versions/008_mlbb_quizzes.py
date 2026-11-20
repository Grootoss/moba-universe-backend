"""Group quizzes by game and role, and load the MLBB set

Revision ID: 008_mlbb_quizzes
Revises: 007_quizzes
Create Date: 2026-11-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_mlbb_quizzes"
down_revision: Union[str, None] = "007_quizzes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quizzes",
        sa.Column("game", sa.String(length=32), nullable=False, server_default="mlbb"),
    )
    op.add_column(
        "quizzes",
        sa.Column("role", sa.String(length=32), nullable=False, server_default=""),
    )
    op.add_column("quizzes", sa.Column("cover_image", sa.String(length=512), nullable=True))
    op.create_index("ix_quizzes_game_role", "quizzes", ["game", "role"])
    from app.quiz_seed import seed_mlbb_quizzes

    seed_mlbb_quizzes(op.get_bind())


def downgrade() -> None:
    import json

    from app.quiz_seed import DATA_PATH

    slugs = [quiz["slug"] for quiz in json.loads(DATA_PATH.read_text(encoding="utf-8"))]
    op.get_bind().execute(
        sa.text("DELETE FROM quizzes WHERE slug = :slug"),
        [{"slug": slug} for slug in slugs],
    )
    op.drop_index("ix_quizzes_game_role", table_name="quizzes")
    op.drop_column("quizzes", "cover_image")
    op.drop_column("quizzes", "role")
    op.drop_column("quizzes", "game")
