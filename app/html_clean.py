"""Drop active markup from guide HTML before it reaches a browser."""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

_DROP_TAGS = frozenset(
    {"script", "style", "iframe", "object", "embed", "form", "link", "meta", "base", "svg"}
)
_URL_ATTRS = frozenset({"href", "src", "xlink:href", "action", "formaction"})
_BAD_URL = re.compile(r"^\s*(?:javascript|data):", re.IGNORECASE)


class _Cleaner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs, close=False)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs, close=True)

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if name in _DROP_TAGS:
            if self._skip:
                self._skip -= 1
            return
        if self._skip:
            return
        self._parts.append(f"</{name}>")

    def handle_data(self, data: str) -> None:
        if self._skip or not data:
            return
        self._parts.append(escape(data))

    def handle_entityref(self, name: str) -> None:
        if not self._skip:
            self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self._skip:
            self._parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        return

    def result(self) -> str:
        return "".join(self._parts)

    def _open(self, tag: str, attrs: list[tuple[str, str | None]], *, close: bool) -> None:
        name = tag.lower()
        if name in _DROP_TAGS:
            if not close:
                self._skip += 1
            return
        if self._skip:
            return
        rendered: list[str] = []
        for key, value in attrs:
            attr = key.lower()
            if attr.startswith("on") or attr in {"srcdoc", "style"}:
                continue
            if value is not None and attr in _URL_ATTRS and _BAD_URL.match(value):
                continue
            if value is None:
                rendered.append(escape(key, quote=True))
            else:
                rendered.append(f'{escape(key, quote=True)}="{escape(value, quote=True)}"')
        tail = " /" if close else ""
        gap = f" {' '.join(rendered)}" if rendered else ""
        self._parts.append(f"<{name}{gap}{tail}>")


def clean_article_html(raw: str | None) -> str:
    text = raw or ""
    if not text.strip():
        return ""
    cleaner = _Cleaner()
    cleaner.feed(text)
    cleaner.close()
    return cleaner.result()
