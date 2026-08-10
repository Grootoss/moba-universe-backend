"""Day 4: username, unlock flag, draft status, moderation notes

Revision ID: 002_day4_auth_profiles
Revises: 001_initial
Create Date: 2026-07-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_day4_auth_profiles"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=64), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "profile_edit_unlocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # Existing seeded users: set username from email local-part where missing
    op.execute(
        """
        UPDATE users
        SET username = split_part(email, '@', 1)
        WHERE username IS NULL
        """
    )
    op.execute(
        """
        UPDATE users
        SET profile_edit_unlocked = true
        WHERE role = 'admin'
           OR email IN ('rootoss@mobauniverse.com', 'player1@mobauniverse.com')
        """
    )
    op.alter_column("users", "username", nullable=False)

    op.add_column(
        "user_profiles",
        sa.Column("moderation_note", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "moderation_note")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "profile_edit_unlocked")
    op.drop_column("users", "username")
