"""Shared category helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category

MLBB_SLUG = "mlbb"


def ensure_mlbb_category(db: Session) -> None:
    exists = db.scalar(select(Category.id).where(Category.slug == MLBB_SLUG).limit(1))
    if exists:
        return
    db.add(Category(slug=MLBB_SLUG, name_ru="MLBB", name_en="MLBB"))
    db.commit()


def list_all_categories(db: Session) -> list[Category]:
    ensure_mlbb_category(db)
    return list(db.scalars(select(Category).order_by(Category.id)).all())
