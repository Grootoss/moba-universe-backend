"""SEO helpers: robots.txt and dynamic sitemap.xml."""

from __future__ import annotations

import logging
from datetime import date, datetime
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Article, ArticleStatus, ModerationStatus, User, UserProfile, UserRole

router = APIRouter(tags=["seo"])
settings = get_settings()
logger = logging.getLogger(__name__)

_STAFF_ROLES = (UserRole.admin.value, UserRole.moderator.value)


def _base() -> str:
    return settings.site_url.rstrip("/")


def _xml(url: str) -> str:
    return escape(url, {'"': "&quot;", "'": "&apos;"})


def _lastmod(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return None


def _url_block(loc: str, alt_loc: str, lang: str, lastmod: str | None) -> list[str]:
    alt_lang = "en" if lang == "ru" else "ru"
    default_loc = loc if lang == "ru" else alt_loc
    lines = [
        "  <url>",
        f"    <loc>{_xml(loc)}</loc>",
        f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{_xml(loc)}" />',
        f'    <xhtml:link rel="alternate" hreflang="{alt_lang}" href="{_xml(alt_loc)}" />',
        f'    <xhtml:link rel="alternate" hreflang="x-default" href="{_xml(default_loc)}" />',
    ]
    if lastmod:
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
    lines.append("  </url>")
    return lines


def _hub_entries(base: str) -> list[tuple[str, str, str, str | None]]:
    """Static public hubs. No lastmod — Google treats a fake 'today' as untrustworthy."""
    pairs = (
        ("/ru", "/en"),
        ("/ru/evergreen", "/en/evergreen"),
        ("/ru/users", "/en/users"),
        ("/ru/privacy", "/en/privacy"),
        ("/ru/terms", "/en/terms"),
    )
    entries: list[tuple[str, str, str, str | None]] = []
    for ru_path, en_path in pairs:
        entries.append((f"{base}{ru_path}", f"{base}{en_path}", "ru", None))
        entries.append((f"{base}{en_path}", f"{base}{ru_path}", "en", None))
    return entries


def _render(entries: list[tuple[str, str, str, str | None]]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for loc, alt_loc, lang, lastmod in entries:
        parts.extend(_url_block(loc, alt_loc, lang, lastmod))
    parts.append("</urlset>")
    parts.append("")
    return "\n".join(parts)


@router.get("/robots.txt", response_class=Response)
def robots_txt():
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
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
    entries = _hub_entries(base)

    try:
        articles = db.execute(
            select(Article.slug, Article.updated_at, Article.created_at)
            .where(Article.status == ArticleStatus.published.value)
            .order_by(Article.id)
        ).all()
        for slug, updated_at, created_at in articles:
            if not slug:
                continue
            stamp = _lastmod(updated_at) or _lastmod(created_at)
            entries.append((f"{base}/ru/evergreen/{slug}", f"{base}/en/evergreen/{slug}", "ru", stamp))
            entries.append((f"{base}/en/evergreen/{slug}", f"{base}/ru/evergreen/{slug}", "en", stamp))
    except Exception:
        logger.exception("sitemap: failed to load articles")
        db.rollback()

    try:
        profiles = db.execute(
            select(UserProfile.user_id, UserProfile.updated_at, UserProfile.created_at)
            .join(User, UserProfile.user_id == User.id)
            .where(
                UserProfile.moderation_status == ModerationStatus.approved.value,
                UserProfile.is_public.is_(True),
                User.role.notin_(_STAFF_ROLES),
            )
            .order_by(UserProfile.user_id)
        ).all()
        for user_id, updated_at, created_at in profiles:
            if not user_id:
                continue
            stamp = _lastmod(updated_at) or _lastmod(created_at)
            entries.append((f"{base}/ru/user/{user_id}", f"{base}/en/user/{user_id}", "ru", stamp))
            entries.append((f"{base}/en/user/{user_id}", f"{base}/ru/user/{user_id}", "en", stamp))
    except Exception:
        logger.exception("sitemap: failed to load profiles")
        db.rollback()

    return Response(content=_render(entries), media_type="application/xml")
