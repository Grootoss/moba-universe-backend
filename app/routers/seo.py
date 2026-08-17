"""SEO helpers: robots.txt and dynamic sitemap.xml."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Article, ArticleStatus, ModerationStatus, User, UserProfile, UserRole

router = APIRouter(tags=["seo"])
settings = get_settings()


def _base() -> str:
    return settings.site_url.rstrip("/")


@router.get("/robots.txt", response_class=Response)
def robots_txt():
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Allow: /ru/",
            "Allow: /en/",
            "Allow: /ru/evergreen",
            "Allow: /en/evergreen",
            "Allow: /ru/privacy",
            "Allow: /en/privacy",
            "Allow: /ru/terms",
            "Allow: /en/terms",
            "Allow: /ru/users",
            "Allow: /en/users",
            "Allow: /ru/user/",
            "Allow: /en/user/",
            "Disallow: /admin",
            "Disallow: /admin/",
            "Disallow: /profile",
            "Disallow: /login",
            "Disallow: /register",
            "Disallow: /ru/profile",
            "Disallow: /en/profile",
            "Disallow: /ru/login",
            "Disallow: /en/login",
            "Disallow: /ru/register",
            "Disallow: /en/register",
            "Disallow: /api/",
            f"Sitemap: {_base()}/sitemap.xml",
            "",
        ]
    )
    return Response(content=body, media_type="text/plain; charset=utf-8")


@router.get("/sitemap.xml", response_class=Response)
def sitemap_xml(db: Session = Depends(get_db)):
    base = _base()
    now = datetime.now(timezone.utc).date().isoformat()

    urls: list[tuple[str, str, str, str, str]] = [
        (f"{base}/ru", f"{base}/en", now, "daily", "ru"),
        (f"{base}/en", f"{base}/ru", now, "daily", "en"),
        (f"{base}/ru/evergreen", f"{base}/en/evergreen", now, "daily", "ru"),
        (f"{base}/en/evergreen", f"{base}/ru/evergreen", now, "daily", "en"),
        (f"{base}/ru/users", f"{base}/en/users", now, "daily", "ru"),
        (f"{base}/en/users", f"{base}/ru/users", now, "daily", "en"),
        (f"{base}/ru/privacy", f"{base}/en/privacy", now, "monthly", "ru"),
        (f"{base}/en/privacy", f"{base}/ru/privacy", now, "monthly", "en"),
        (f"{base}/ru/terms", f"{base}/en/terms", now, "monthly", "ru"),
        (f"{base}/en/terms", f"{base}/ru/terms", now, "monthly", "en"),
    ]

    articles = db.scalars(
        select(Article)
        .where(Article.status == ArticleStatus.published.value)
        .order_by(Article.id)
    ).all()
    for a in articles:
        lastmod = a.updated_at or a.created_at
        stamp = lastmod.date().isoformat() if lastmod else now
        urls.append((f"{base}/ru/evergreen/{a.slug}", f"{base}/en/evergreen/{a.slug}", stamp, "weekly", "ru"))
        urls.append((f"{base}/en/evergreen/{a.slug}", f"{base}/ru/evergreen/{a.slug}", stamp, "weekly", "en"))

    profiles = db.scalars(
        select(UserProfile)
        .join(User, UserProfile.user_id == User.id)
        .where(
            UserProfile.moderation_status == ModerationStatus.approved.value,
            UserProfile.is_public.is_(True),
            User.role.not_in((UserRole.admin.value, UserRole.moderator.value)),
        )
        .order_by(UserProfile.user_id)
    ).all()
    for p in profiles:
        lastmod = p.updated_at or p.created_at
        stamp = lastmod.date().isoformat() if lastmod else now
        urls.append((f"{base}/ru/user/{p.user_id}", f"{base}/en/user/{p.user_id}", stamp, "weekly", "ru"))
        urls.append((f"{base}/en/user/{p.user_id}", f"{base}/ru/user/{p.user_id}", stamp, "weekly", "en"))

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for loc, alt_loc, lastmod, changefreq, lang in urls:
        alt_lang = "en" if lang == "ru" else "ru"
        default_loc = loc if lang == "en" else alt_loc
        parts.append("  <url>")
        parts.append(f"    <loc>{loc}</loc>")
        parts.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{loc}" />')
        parts.append(f'    <xhtml:link rel="alternate" hreflang="{alt_lang}" href="{alt_loc}" />')
        parts.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{default_loc}" />')
        parts.append(f"    <lastmod>{lastmod}</lastmod>")
        parts.append(f"    <changefreq>{changefreq}</changefreq>")
        parts.append("  </url>")
    parts.append("</urlset>")
    parts.append("")

    return Response(content="\n".join(parts), media_type="application/xml; charset=utf-8")
