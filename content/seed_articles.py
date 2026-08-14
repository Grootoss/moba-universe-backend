"""Seed catalog: article categories only (articles are added via admin)."""

from __future__ import annotations

from typing import Any

CATEGORIES = [
    {"slug": "ranks", "name_ru": "Ранги", "name_en": "Ranks"},
    {"slug": "replays", "name_ru": "Реплеи", "name_en": "Replays"},
    {"slug": "roles", "name_ru": "Роли", "name_en": "Roles"},
    {"slug": "heroes", "name_ru": "Герои", "name_en": "Heroes"},
    {"slug": "macro", "name_ru": "Макро", "name_en": "Macro"},
    {"slug": "mental", "name_ru": "Менталка", "name_en": "Mental"},
    {"slug": "draft", "name_ru": "Драфт", "name_en": "Draft"},
    {"slug": "beginners", "name_ru": "Новичкам", "name_en": "Beginners"},
    {"slug": "mlbb", "name_ru": "MLBB", "name_en": "MLBB"},
]

articles: list[dict[str, Any]] = []
