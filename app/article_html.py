"""Standalone article HTML for crawlers when the SPA snapshot is not built yet."""

from __future__ import annotations

import json
from datetime import datetime
from html import escape

from app.models import Article, ArticleTranslation

_ROBOTS = "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"


def _pick(article: Article, lang: str) -> ArticleTranslation | None:
    by_lang = {tr.lang: tr for tr in article.translations}
    return by_lang.get(lang) or by_lang.get("ru") or by_lang.get("en")


def _stamp(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.date().isoformat()


def render_article_html(article: Article, lang: str, site_url: str) -> str | None:
    tr = _pick(article, lang)
    if tr is None:
        return None
    base = site_url.rstrip("/")
    ru = f"{base}/ru/evergreen/{article.slug}"
    en = f"{base}/en/evergreen/{article.slug}"
    canonical = ru if lang == "ru" else en
    title = tr.title.strip()
    description = (tr.excerpt or title).strip()[:300]
    published = _stamp(article.created_at)
    modified = _stamp(article.updated_at) or published
    home = f"{base}/{lang}"
    guides = f"{base}/{lang}/evergreen"
    home_label = "Главная" if lang == "ru" else "Home"
    guides_label = "Гайды" if lang == "ru" else "Guides"
    other_href = en if lang == "ru" else ru
    other_label = "English" if lang == "ru" else "Русский"

    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "headline": title,
                "description": description,
                "inLanguage": lang,
                "mainEntityOfPage": canonical,
                "url": canonical,
                "datePublished": article.created_at.isoformat() if article.created_at else None,
                "dateModified": article.updated_at.isoformat() if article.updated_at else None,
                "author": {"@type": "Organization", "name": "Moba Universe", "url": base},
                "publisher": {"@type": "Organization", "name": "Moba Universe", "url": base},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": home_label, "item": home},
                    {"@type": "ListItem", "position": 2, "name": guides_label, "item": guides},
                    {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
                ],
            },
        ],
    }
    json_ld = json.dumps(graph, ensure_ascii=False).replace("<", "\\u003c")
    extra = ""
    example = (tr.mlbb_example or "").strip()
    if example:
        heading = "Пример" if lang == "ru" else "Example"
        extra = f"<section><h2>{heading}</h2>{example}</section>"
    dates = ""
    if published:
        dates = f"<p class='meta'>{escape(published)}"
        if modified and modified != published:
            dates += f" · {escape(modified)}"
        dates += "</p>"

    return f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} | Moba Universe</title>
  <meta name="description" content="{escape(description)}">
  <meta name="robots" content="{_ROBOTS}">
  <link rel="canonical" href="{escape(canonical)}">
  <link rel="alternate" hreflang="ru" href="{escape(ru)}">
  <link rel="alternate" hreflang="en" href="{escape(en)}">
  <link rel="alternate" hreflang="x-default" href="{escape(ru)}">
  <link rel="alternate" type="application/rss+xml" title="Moba Universe" href="{escape(base)}/feed.xml">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:locale" content="{'ru_RU' if lang == 'ru' else 'en_US'}">
  <meta property="og:site_name" content="Moba Universe">
  <script type="application/ld+json">{json_ld}</script>
  <style>
    body {{ margin: 0; background: #0c0e14; color: #eef0f6; font: 18px/1.65 "Segoe UI", system-ui, sans-serif; }}
    header, main {{ width: min(720px, calc(100% - 2rem)); margin: 0 auto; }}
    header {{ padding: 1.25rem 0; }}
    a {{ color: #a5b4fc; }}
    h1 {{ font-size: 2rem; line-height: 1.2; letter-spacing: -0.03em; }}
    .crumbs {{ color: #9aa3b8; font-size: 0.9rem; }}
    .meta {{ color: #9aa3b8; }}
    article :is(p, li) {{ margin: 0.8rem 0; }}
    .lang {{ margin: 2rem 0 3rem; }}
  </style>
</head>
<body>
  <header>
    <a href="{escape(home)}">Moba Universe</a>
    <p class="crumbs"><a href="{escape(home)}">{home_label}</a> / <a href="{escape(guides)}">{guides_label}</a> / {escape(title)}</p>
  </header>
  <main>
    <article>
      <h1>{escape(title)}</h1>
      {dates}
      {tr.content}
      {extra}
    </article>
    <p class="lang"><a href="{escape(other_href)}">{other_label}</a></p>
  </main>
</body>
</html>
"""
