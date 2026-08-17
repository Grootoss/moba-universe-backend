from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.category_helpers import list_all_categories
from app.database import get_db
from app.deps import require_admin, require_moderator
from app.media import derive_cover_thumb
from app.models import (
    Article,
    ArticleStatus,
    ArticleTranslation,
    Category,
    ModerationStatus,
    User,
    UserProfile,
)
from app.schemas import (
    AdminProfileOut,
    ArticleAdminOut,
    ArticleCreateIn,
    ArticleUpdateIn,
    CategoryOut,
    GameRankOut,
    ProfileModerateIn,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _profile_admin(profile: UserProfile) -> AdminProfileOut:
    user = profile.user
    raw = profile.social_links or {}
    if isinstance(raw, list):
        social_links = {
            str(item.get("label")): str(item.get("url"))
            for item in raw
            if isinstance(item, dict) and item.get("label") and item.get("url")
        }
        contacts = [
            {
                "label": str(item.get("label")),
                "url": str(item.get("url")),
                "is_public": bool(item.get("is_public")),
            }
            for item in raw
            if isinstance(item, dict) and item.get("label") and item.get("url")
        ]
    else:
        social_links = raw if isinstance(raw, dict) else {}
        contacts = []
    return AdminProfileOut(
        id=profile.user_id,
        user_id=profile.user_id,
        email=user.email if user else None,
        username=user.username if user else None,
        nickname=profile.nickname,
        bio=profile.bio,
        telegram_url=profile.telegram_url,
        social_links=social_links,
        contacts=contacts,
        games=[
            GameRankOut(
                game=g.game,
                rank=g.rank,
                roles=[str(r) for r in (g.roles or [])],
                sort_order=g.sort_order,
            )
            for g in profile.game_ranks
        ],
        moderation_status=profile.moderation_status,
        moderation_note=profile.moderation_note or "",
        is_public=profile.is_public,
        profile_edit_unlocked=bool(user.profile_edit_unlocked) if user else False,
    )


@router.get("/profiles", response_model=list[AdminProfileOut])
def admin_list_profiles(_: User = Depends(require_moderator), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(UserProfile)
        .options(selectinload(UserProfile.game_ranks), selectinload(UserProfile.user))
        .order_by(UserProfile.user_id)
    ).all()
    return [_profile_admin(p) for p in rows]


@router.post("/profiles/{user_id}/unlock", response_model=AdminProfileOut)
def admin_unlock_profile(
    user_id: int,
    _: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """Allow the user to edit their profile cabinet (first-time registration approval)."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .options(selectinload(UserProfile.game_ranks), selectinload(UserProfile.user))
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    user.profile_edit_unlocked = True
    db.commit()
    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .options(selectinload(UserProfile.game_ranks), selectinload(UserProfile.user))
    )
    return _profile_admin(profile)  # type: ignore[arg-type]


@router.patch("/profiles/{user_id}", response_model=AdminProfileOut)
def admin_moderate_profile(
    user_id: int,
    body: ProfileModerateIn,
    _: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    if body.moderation_status not in {s.value for s in ModerationStatus}:
        raise HTTPException(status_code=400, detail="Invalid moderation_status")

    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .options(selectinload(UserProfile.game_ranks), selectinload(UserProfile.user))
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if body.moderation_status == ModerationStatus.rejected.value:
        note = (body.moderation_note or "").strip()
        if not note:
            raise HTTPException(status_code=400, detail="moderation_note is required when rejecting")
        profile.moderation_note = note
        profile.is_public = False
    elif body.moderation_status == ModerationStatus.approved.value:
        profile.moderation_note = ""
        # Approve always publishes the public profile page
        profile.is_public = True
        if profile.user:
            profile.user.profile_edit_unlocked = True
    else:
        if body.moderation_note is not None:
            profile.moderation_note = body.moderation_note.strip()
        if body.is_public is not None:
            profile.is_public = body.is_public

    profile.moderation_status = body.moderation_status
    db.commit()
    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .options(selectinload(UserProfile.game_ranks), selectinload(UserProfile.user))
    )
    return _profile_admin(profile)  # type: ignore[arg-type]


def _article_admin(article: Article) -> ArticleAdminOut:
    by_lang = {t.lang: t for t in article.translations}
    ru = by_lang.get("ru")
    en = by_lang.get("en")
    return ArticleAdminOut(
        id=article.id,
        slug=article.slug,
        status=article.status,
        category=article.category.slug if article.category else None,
        cover_image=article.cover_image,
        cover_thumb=derive_cover_thumb(article.cover_image, article.cover_thumb),
        title_ru=ru.title if ru else None,
        title_en=en.title if en else None,
        excerpt_ru=ru.excerpt if ru else None,
        excerpt_en=en.excerpt if en else None,
        content_ru=ru.content if ru else None,
        content_en=en.content if en else None,
        mlbb_example_ru=ru.mlbb_example if ru else None,
        mlbb_example_en=en.mlbb_example if en else None,
    )


@router.get("/categories", response_model=list[CategoryOut])
def admin_list_categories(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = list_all_categories(db)
    return [CategoryOut(slug=c.slug, name_ru=c.name_ru, name_en=c.name_en) for c in rows]


@router.get("/articles", response_model=list[ArticleAdminOut])
def admin_list_articles(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Article)
        .options(selectinload(Article.translations), selectinload(Article.category))
        .order_by(Article.id)
    ).all()
    return [_article_admin(a) for a in rows]


@router.get("/articles/{article_id}", response_model=ArticleAdminOut)
def admin_get_article(article_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    article = db.scalar(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.translations), selectinload(Article.category))
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_admin(article)


@router.post("/articles", response_model=ArticleAdminOut)
def admin_create_article(
    body: ArticleCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.scalar(select(Article).where(Article.slug == body.slug)):
        raise HTTPException(status_code=400, detail="Slug already exists")
    category = None
    if body.category_slug:
        category = db.scalar(select(Category).where(Category.slug == body.category_slug))
    article = Article(
        slug=body.slug,
        category=category,
        author_id=admin.id,
        status=body.status if body.status in {s.value for s in ArticleStatus} else ArticleStatus.draft.value,
        cover_image=(body.cover_image or "").strip() or None,
        cover_thumb=(body.cover_thumb or "").strip() or None,
    )
    for lang, tr in body.translations.items():
        article.translations.append(
            ArticleTranslation(
                lang=lang,
                title=tr.title,
                excerpt=tr.excerpt,
                content=tr.content,
                mlbb_example=tr.mlbb_example or "",
            )
        )
    db.add(article)
    db.commit()
    db.refresh(article)
    article = db.scalar(
        select(Article)
        .where(Article.id == article.id)
        .options(selectinload(Article.translations), selectinload(Article.category))
    )
    return _article_admin(article)


@router.put("/articles/{article_id}", response_model=ArticleAdminOut)
@router.patch("/articles/{article_id}", response_model=ArticleAdminOut)
def admin_update_article(
    article_id: int,
    body: ArticleUpdateIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    article = db.scalar(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.translations), selectinload(Article.category))
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if body.slug and body.slug != article.slug:
        if db.scalar(select(Article).where(Article.slug == body.slug)):
            raise HTTPException(status_code=400, detail="Slug already exists")
        article.slug = body.slug
    if body.status:
        article.status = body.status
    if body.cover_image is not None:
        article.cover_image = body.cover_image.strip() or None
    if body.cover_thumb is not None:
        article.cover_thumb = body.cover_thumb.strip() or None
    if body.category_slug is not None:
        article.category = db.scalar(select(Category).where(Category.slug == body.category_slug))
    if body.translations:
        existing = {t.lang: t for t in article.translations}
        for lang, tr in body.translations.items():
            if lang in existing:
                existing[lang].title = tr.title
                existing[lang].excerpt = tr.excerpt
                existing[lang].content = tr.content
                existing[lang].mlbb_example = tr.mlbb_example or ""
            else:
                article.translations.append(
                    ArticleTranslation(
                        lang=lang,
                        title=tr.title,
                        excerpt=tr.excerpt,
                        content=tr.content,
                        mlbb_example=tr.mlbb_example or "",
                    )
                )
    db.commit()
    article = db.scalar(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.translations), selectinload(Article.category))
    )
    return _article_admin(article)


@router.delete("/articles/{article_id}")
def admin_delete_article(
    article_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"ok": True}
