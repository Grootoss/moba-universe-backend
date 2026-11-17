from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.html_clean import clean_article_html
from app.media import derive_cover_thumb
from app.models import Article, ArticleStatus, ArticleTranslation, Category
from app.schemas import ArticleCardOut, ArticleListItemOut, ArticleListOut

router = APIRouter(prefix="/api/evergreen/articles", tags=["articles"])


def _article_to_public(article: Article) -> ArticleListItemOut:
    translations = {
        tr.lang: {
            "title": tr.title,
            "excerpt": tr.excerpt,
            "text": clean_article_html(tr.content),
            "mlbb_example": clean_article_html(tr.mlbb_example),
        }
        for tr in article.translations
    }
    return ArticleListItemOut(
        id_article=article.id,
        slug=article.slug,
        category=article.category.slug if article.category else None,
        cover_image=article.cover_image,
        cover_thumb=derive_cover_thumb(article.cover_image, article.cover_thumb),
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
        cover_thumb=derive_cover_thumb(article.cover_image, article.cover_thumb),
        title=tr.title,
        excerpt=tr.excerpt,
        text=clean_article_html(tr.content),
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def _article_card(article: Article, lang: str) -> ArticleCardOut:
    by_lang = {tr.lang: tr for tr in article.translations}
    tr = by_lang.get(lang) or by_lang.get("en") or by_lang.get("ru")
    return ArticleCardOut(
        id_article=article.id,
        slug=article.slug,
        category=article.category.slug if article.category else None,
        cover_image=article.cover_image,
        cover_thumb=derive_cover_thumb(article.cover_image, article.cover_thumb),
        title=tr.title if tr else article.slug,
        excerpt=(tr.excerpt if tr else "") or "",
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


@router.get("")
def list_articles(
    response: Response,
    lang: str = Query("ru", description="ru or en — list returns that language only"),
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
    response.headers["Cache-Control"] = "public, max-age=60"
    filters = [Article.status == ArticleStatus.published.value]
    search = (q or "").strip()
    if search:
        filters.append(Article.translations.any(ArticleTranslation.title.ilike(f"%{search}%")))
    category_slug = (category or "").strip()
    if category_slug:
        filters.append(Article.category.has(Category.slug == category_slug))

    active_lang = lang if lang in ("ru", "en") else "ru"
    total = db.scalar(select(func.count()).select_from(Article).where(*filters)) or 0
    rows = db.execute(
        select(
            Article.id.label("id"),
            Article.slug.label("slug"),
            Article.cover_image.label("cover_image"),
            Article.cover_thumb.label("cover_thumb"),
            Article.created_at.label("created_at"),
            Article.updated_at.label("updated_at"),
            Category.slug.label("category_slug"),
            ArticleTranslation.title.label("title"),
            ArticleTranslation.excerpt.label("excerpt"),
        )
        .outerjoin(
            ArticleTranslation,
            and_(
                ArticleTranslation.article_id == Article.id,
                ArticleTranslation.lang == active_lang,
            ),
        )
        .outerjoin(Category, Category.id == Article.category_id)
        .where(*filters)
        .order_by(Article.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        ArticleCardOut(
            id_article=row.id,
            slug=row.slug,
            category=row.category_slug,
            cover_image=row.cover_image,
            cover_thumb=derive_cover_thumb(row.cover_image, row.cover_thumb),
            title=row.title or row.slug,
            excerpt=row.excerpt or "",
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
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
