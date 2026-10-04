"""Crawler HTML for the home page and the guides hub."""

from __future__ import annotations

import json
from html import escape

_ROBOTS = "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"

_COPY = {
    "ru": {
        "title": "Moba Universe",
        "description": "Фан-сайт по MOBA-играм: гайды и личные страницы игроков.",
        "guides": "Гайды",
        "guides_text": "Стратегии, ранги и разборы по Moba играм.",
        "users": "Пользователи",
        "users_text": "Профили игроков.",
        "hub_title": "Гайды Moba Universe",
        "hub_description": "Стратегии, ранги и разбор MOBA-игр",
        "empty": "Пока что нет статей",
        "other": "English",
    },
    "en": {
        "title": "Moba Universe",
        "description": "A fan site for MOBA games: guides and personal player pages.",
        "guides": "Guides",
        "guides_text": "Strategies, ranks, and breakdowns for MOBA games.",
        "users": "Users",
        "users_text": "Player profiles.",
        "hub_title": "Moba Universe Guides",
        "hub_description": "Strategies, ranks, and MOBA game breakdowns",
        "empty": "No articles yet",
        "other": "Русский",
    },
}


def _page(lang: str, title: str, description: str, canonical: str, ru: str, en: str, body: str) -> str:
    other = en if lang == "ru" else ru
    other_label = _COPY[lang]["other"]
    graph = {
        "@context": "https://schema.org",
        "@type": "WebSite" if canonical.rstrip("/").endswith(("/ru", "/en")) else "CollectionPage",
        "name": title,
        "description": description,
        "url": canonical,
        "inLanguage": lang,
    }
    json_ld = json.dumps(graph, ensure_ascii=False).replace("<", "\\u003c")
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
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{escape(canonical)}">
  <meta property="og:site_name" content="Moba Universe">
  <script type="application/ld+json">{json_ld}</script>
  <style>
    body {{ margin: 0; background: #0c0e14; color: #eef0f6; font: 18px/1.65 "Segoe UI", system-ui, sans-serif; }}
    main {{ width: min(720px, calc(100% - 2rem)); margin: 0 auto; padding: 2rem 0 3rem; }}
    a {{ color: #a5b4fc; }}
    h1 {{ font-size: 2rem; line-height: 1.2; }}
    li {{ margin: 0.8rem 0; }}
  </style>
</head>
<body>
  <main>
    {body}
    <p><a href="{escape(other)}">{escape(other_label)}</a></p>
  </main>
</body>
</html>
"""


def render_home_html(lang: str, site_url: str) -> str:
    copy = _COPY[lang]
    base = site_url.rstrip("/")
    ru = f"{base}/ru"
    en = f"{base}/en"
    canonical = ru if lang == "ru" else en
    body = f"""
    <h1>{escape(copy["title"])}</h1>
    <p>{escape(copy["description"])}</p>
    <ul>
      <li><a href="{escape(canonical)}/evergreen">{escape(copy["guides"])}</a> — {escape(copy["guides_text"])}</li>
      <li><a href="{escape(canonical)}/users">{escape(copy["users"])}</a> — {escape(copy["users_text"])}</li>
    </ul>
    """
    return _page(lang, copy["title"], copy["description"], canonical, ru, en, body)


def render_guides_html(
    lang: str,
    site_url: str,
    articles: list[tuple[str, str, str]],
) -> str:
    copy = _COPY[lang]
    base = site_url.rstrip("/")
    ru = f"{base}/ru/evergreen"
    en = f"{base}/en/evergreen"
    canonical = ru if lang == "ru" else en
    if articles:
        items = []
        for slug, title, excerpt in articles:
            href = f"{canonical}/{slug}"
            line = f'<a href="{escape(href)}">{escape(title)}</a>'
            if excerpt.strip():
                line += f" — {escape(excerpt.strip())}"
            items.append(f"<li>{line}</li>")
        listing = "<ul>" + "".join(items) + "</ul>"
    else:
        listing = f"<p>{escape(copy['empty'])}</p>"
    body = f"<h1>{escape(copy['hub_title'])}</h1><p>{escape(copy['hub_description'])}</p>{listing}"
    return _page(lang, copy["hub_title"], copy["hub_description"], canonical, ru, en, body)
