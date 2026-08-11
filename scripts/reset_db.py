"""Drop all tables, recreate schema, and seed fresh data (Rootoss + admin, no articles)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.database import Base, engine
from scripts.seed import seed

ROOT = Path(__file__).resolve().parents[1]


def reset_database() -> None:
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Stamping Alembic head...")
    command.stamp(Config(str(ROOT / "alembic.ini")), "head")
    print("Seeding...")
    seed()
    print("Database reset complete.")


if __name__ == "__main__":
    reset_database()
