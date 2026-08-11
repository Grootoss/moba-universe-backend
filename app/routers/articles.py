from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Article, ArticleStatus, ArticleTranslation, Category
from app.schemas import ArticleListItemOut, ArticleListOut

router = APIRouter(prefix="/api/evergreen/articles", tags=["articles"])


def _article_to_public(article: Article) -> ArticleListItemOut:
    translations = {
        tr.lang: {
            "title": tr.title,
            "excerpt": tr.excerpt,
            "text": tr.content,
            "mlbb_example": tr.mlbb_example or "",
        }
        for tr in article.translations
    }
    return ArticleListItemOut(
        id_article=article.id,
        slug=article.slug,
        category=article.category.slug if article.category else None,
        cover_image=article.cover_image,
        translations=translations,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def _article_flat(article: Article, lang: str) -> ArticleListItemOut:
    by_lang = {tr.lang: tr for tr in article.translations}
    tr = by_lang.get(lang) or by_lang.get("en") or by_lang.get("ru")
    if not tr:
        raise HTTPException(status_code=404, detail="Translation not found")
    return ArticleListItemOut(
        id_article=article.id,
        slug=article.slug,
        category=article.category.slug if article.category else None,
        cover_image=article.cover_image,
        title=tr.title,
        excerpt=tr.excerpt,
        text=tr.content,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def _map_rows(rows: list[Article], lang: str | None) -> list[ArticleListItemOut]:
    if lang in ("ru", "en"):
        return [_article_flat(a, lang) for a in rows]
    return [_article_to_public(a) for a in rows]


@router.get("")
def list_articles(
    lang: str | None = None,
    q: str | None = Query(None, description="Search in article titles"),
    category: str | None = Query(None, description="Filter by category slug"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    paginated: bool = Query(
        False,
        description="true → {items,total,page,page_size}; false → plain array (legacy)",
    ),
    db: Session = Depends(get_db),
):
    filters = [Article.status == ArticleStatus.published.value]
    search = (q or "").strip()
    if search:
        filters.append(Article.translations.any(ArticleTranslation.title.ilike(f"%{search}%")))
    category_slug = (category or "").strip()
    if category_slug:
        filters.append(Article.category.has(Category.slug == category_slug))

    total = db.scalar(select(func.count()).select_from(Article).where(*filters)) or 0
    rows = db.scalars(
        select(Article)
        .where(*filters)
        .options(selectinload(Article.translations), selectinload(Article.category))
        .order_by(Article.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = _map_rows(list(rows), lang)
    if paginated:
        return ArticleListOut(items=items, total=total, page=page, page_size=page_size)
    return items


@router.get("/{slug}")
def get_article(slug: str, lang: str | None = None, db: Session = Depends(get_db)):
    article = db.scalar(
        select(Article)
        .where(Article.slug == slug, Article.status == ArticleStatus.published.value)
        .options(selectinload(Article.translations), selectinload(Article.category))
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if lang in ("ru", "en"):
        return _article_flat(article, lang)
    return _article_to_public(article)
