"""Initial schema: users, profiles, games, articles

Revision ID: 001_initial
Revises:
Create Date: 2026-07-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name_ru", sa.String(length=120), nullable=False),
        sa.Column("name_en", sa.String(length=120), nullable=False),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nickname", sa.String(length=80), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False),
        sa.Column("telegram_url", sa.String(length=255), nullable=True),
        sa.Column("social_links", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("moderation_status", sa.String(length=20), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "user_game_ranks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game", sa.String(length=20), nullable=False),
        sa.Column("rank", sa.String(length=80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("profile_id", "game", name="uq_profile_game"),
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("cover_image", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_articles_slug", "articles", ["slug"], unique=True)

    op.create_table(
        "article_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.UniqueConstraint("article_id", "lang", name="uq_article_lang"),
    )


def downgrade() -> None:
    op.drop_table("article_translations")
    op.drop_index("ix_articles_slug", table_name="articles")
    op.drop_table("articles")
    op.drop_table("user_game_ranks")
    op.drop_table("user_profiles")
    op.drop_table("categories")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
