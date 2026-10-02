"""SEO helpers: robots.txt and dynamic sitemap.xml."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from xml.sax.saxutils import escape

from email.utils import format_datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.article_html import render_article_html
from app.config import get_settings
from app.database import SessionLocal, get_db
from app.indexnow import INDEXNOW_KEY
from app.models import Article, ArticleStatus

router = APIRouter(tags=["seo"])
settings = get_settings()
logger = logging.getLogger(__name__)


def _base() -> str:
    return settings.site_url.rstrip("/")


_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _xml(url: str) -> str:
    clean = _ILLEGAL_XML.sub("", url)
    return escape(clean, {'"': "&quot;", "'": "&apos;"})


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


@router.api_route("/robots.txt", methods=["GET", "HEAD"], response_class=Response)
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
            "Clean-param: utm_source&utm_medium&utm_campaign&utm_content&utm_term&gclid&yclid&fbclid",
            f"Sitemap: {_base()}/sitemap.xml",
            "",
        ]
    )
    return Response(content=body, media_type="text/plain; charset=utf-8")


def _safe_rollback(db) -> None:
    try:
        db.rollback()
    except Exception:
        logger.exception("sitemap: rollback failed")


def _load_entries(db) -> list[tuple[str, str, str, str | None]]:
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
        _safe_rollback(db)

    return entries


def _open_session(request: Request):
    """Use the test override when present; otherwise open a short-lived session."""
    override = request.app.dependency_overrides.get(get_db)
    if override is not None:
        gen = override()
        return next(gen), False
    return SessionLocal(), True


def _build_sitemap(request: Request) -> str:
    """Always return XML. A dead database must not become HTTP 500."""
    db = None
    owned = False
    try:
        db, owned = _open_session(request)
        return _render(_load_entries(db))
    except Exception:
        logger.exception("sitemap: failed to build")
        return _render(_hub_entries(_base()))
    finally:
        if owned and db is not None:
            try:
                db.close()
            except Exception:
                logger.exception("sitemap: close failed")


@router.api_route("/sitemap.xml", methods=["GET", "HEAD"], response_class=Response)
def sitemap_xml(request: Request):
    # FastAPI 0.139 registers GET without implicit HEAD. Crawlers send HEAD;
    # a 405 with Content-Length and an empty body stalls the nginx upstream
    # until proxy_read_timeout and the next real GET comes back as 500.
    return Response(
        content=_build_sitemap(request),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=300"},
    )


def _published_articles(db: Session) -> list[Article]:
    rows = db.scalars(
        select(Article)
        .where(Article.status == ArticleStatus.published.value)
        .options(selectinload(Article.translations))
        .order_by(Article.id.desc())
    ).all()
    return list(rows)


@router.api_route("/feed.xml", methods=["GET", "HEAD"], response_class=Response)
def feed_xml(db: Session = Depends(get_db)):
    base = _base()
    items: list[str] = []
    for article in _published_articles(db):
        by_lang = {tr.lang: tr for tr in article.translations}
        for lang in ("ru", "en"):
            tr = by_lang.get(lang)
            if not tr:
                continue
            link = f"{base}/{lang}/evergreen/{article.slug}"
            when = article.updated_at or article.created_at
            pub = format_datetime(when) if when else ""
            items.append(
                "\n".join(
                    [
                        "    <item>",
                        f"      <title>{_xml(tr.title)}</title>",
                        f"      <link>{_xml(link)}</link>",
                        f"      <guid>{_xml(link)}</guid>",
                        f"      <description>{_xml((tr.excerpt or tr.title)[:300])}</description>",
                        f"      <pubDate>{pub}</pubDate>",
                        "    </item>",
                    ]
                )
            )
    body = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0">',
            "  <channel>",
            "    <title>Moba Universe</title>",
            f"    <link>{_xml(base)}/ru/evergreen</link>",
            "    <description>Moba Universe guides</description>",
            *items,
            "  </channel>",
            "</rss>",
            "",
        ]
    )
    return Response(content=body, media_type="application/rss+xml")


@router.api_route(f"/{INDEXNOW_KEY}.txt", methods=["GET", "HEAD"])
def indexnow_key_file():
    return Response(content=INDEXNOW_KEY, media_type="text/plain")


@router.get("/seo/page/{lang}/evergreen/{slug}")
def article_page(lang: str, slug: str, db: Session = Depends(get_db)):
    if lang not in ("ru", "en"):
        raise HTTPException(status_code=404, detail="Article not found")
    article = db.scalar(
        select(Article)
        .where(Article.slug == slug, Article.status == ArticleStatus.published.value)
        .options(selectinload(Article.translations))
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    html = render_article_html(article, lang, _base())
    if not html:
        raise HTTPException(status_code=404, detail="Article not found")
    return HTMLResponse(
        content=html,
        headers={
            "X-Robots-Tag": "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1",
            "Cache-Control": "public, max-age=300",
        },
    )
