from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category
from app.schemas import CategoryOut

router = APIRouter(prefix="/api/evergreen/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    rows = db.scalars(select(Category).order_by(Category.id)).all()
    return [CategoryOut(slug=c.slug, name_ru=c.name_ru, name_en=c.name_en) for c in rows]
