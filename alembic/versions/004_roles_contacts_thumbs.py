"""Roles on game ranks, contact requests, article cover thumbs

Revision ID: 004_roles_contacts_thumbs
Revises: 003_category_mlbb
Create Date: 2026-08-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_roles_contacts_thumbs"
down_revision: Union[str, None] = "003_category_mlbb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_game_ranks",
        sa.Column("roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.alter_column("user_game_ranks", "roles", server_default=None)

    op.add_column("articles", sa.Column("cover_thumb", sa.String(length=512), nullable=True))

    op.create_table(
        "contact_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("requester_id", "target_id", name="uq_contact_pair"),
    )
    op.create_index("ix_contact_requests_requester_id", "contact_requests", ["requester_id"])
    op.create_index("ix_contact_requests_target_id", "contact_requests", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_contact_requests_target_id", table_name="contact_requests")
    op.drop_index("ix_contact_requests_requester_id", table_name="contact_requests")
    op.drop_table("contact_requests")
    op.drop_column("articles", "cover_thumb")
    op.drop_column("user_game_ranks", "roles")
