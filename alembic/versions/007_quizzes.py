"""Public quizzes with bilingual questions, answers, and score results

Revision ID: 007_quizzes
Revises: 006_token_version
Create Date: 2026-11-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_quizzes"
down_revision: Union[str, None] = "006_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_quizzes_slug", "quizzes", ["slug"], unique=True)

    op.create_table(
        "quiz_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.UniqueConstraint("quiz_id", "lang", name="uq_quiz_lang"),
    )

    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("image", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_quiz_questions_quiz_id", "quiz_questions", ["quiz_id"])

    op.create_table(
        "quiz_question_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("quiz_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.UniqueConstraint("question_id", "lang", name="uq_quiz_question_lang"),
    )

    op.create_table(
        "quiz_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("quiz_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_quiz_options_question_id", "quiz_options", ["question_id"])

    op.create_table(
        "quiz_option_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "option_id",
            sa.Integer(),
            sa.ForeignKey("quiz_options.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.UniqueConstraint("option_id", "lang", name="uq_quiz_option_lang"),
    )

    op.create_table(
        "quiz_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("min_correct", sa.Integer(), nullable=False),
        sa.Column("max_correct", sa.Integer(), nullable=False),
    )
    op.create_index("ix_quiz_results_quiz_id", "quiz_results", ["quiz_id"])

    op.create_table(
        "quiz_result_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "result_id",
            sa.Integer(),
            sa.ForeignKey("quiz_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.UniqueConstraint("result_id", "lang", name="uq_quiz_result_lang"),
    )


def downgrade() -> None:
    op.drop_table("quiz_result_translations")
    op.drop_table("quiz_results")
    op.drop_table("quiz_option_translations")
    op.drop_table("quiz_options")
    op.drop_table("quiz_question_translations")
    op.drop_table("quiz_questions")
    op.drop_table("quiz_translations")
    op.drop_index("ix_quizzes_slug", table_name="quizzes")
    op.drop_table("quizzes")
