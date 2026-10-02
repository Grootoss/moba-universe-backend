"""Tell Yandex about article URLs. The key file is public by design."""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

INDEXNOW_KEY = "7f3a9c2e1b84d056a4e8c17b90d2f6a3"
INDEXNOW_ENDPOINT = "https://yandex.com/indexnow"


def article_urls(site_url: str, slug: str) -> list[str]:
    base = site_url.rstrip("/")
    return [f"{base}/ru/evergreen/{slug}", f"{base}/en/evergreen/{slug}"]


def notify_indexnow(site_url: str, urls: list[str]) -> None:
    """Fire-and-forget. A failed ping must not break saving an article."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    clean = [u for u in urls if u.startswith("https://")]
    if not clean:
        return
    host = urlparse(site_url).hostname or ""
    if host != "mobauniverse.com":
        return

    payload = json.dumps(
        {
            "host": host,
            "key": INDEXNOW_KEY,
            "keyLocation": f"https://{host}/{INDEXNOW_KEY}.txt",
            "urlList": clean[:100],
        }
    ).encode("utf-8")

    def send() -> None:
        request = urllib.request.Request(
            INDEXNOW_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                response.read()
        except Exception:
            logger.exception("indexnow: ping failed")

    threading.Thread(target=send, daemon=True).start()
