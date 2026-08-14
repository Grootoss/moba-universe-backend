from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.category_helpers import list_all_categories
from app.database import get_db
from app.schemas import CategoryOut

router = APIRouter(prefix="/api/evergreen/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    rows = list_all_categories(db)
    return [CategoryOut(slug=c.slug, name_ru=c.name_ru, name_en=c.name_en) for c in rows]
