"""Parse the bilingual quiz markdown used in moba-universe-docs/tests."""

from __future__ import annotations

import re
from pathlib import Path

ROLES = ("roam", "mid", "jungle", "exp", "gold")

ROLE_ORDER: dict[str, list[str]] = {
    "roam": [
        "roam-basics",
        "roam-vision",
        "roam-farm",
        "roam-rotations",
        "roam-turtle",
        "roam-lord",
        "roam-gold-lane",
        "roam-mid",
        "roam-exp",
        "roam-jungle",
        "roam-tank",
        "roam-support",
        "roam-ganks",
        "roam-peel",
        "roam-early-game",
        "roam-late-game",
        "roam-recall",
        "roam-mistakes",
        "roam-map",
        "roam-teamfights",
    ],
    "mid": [
        "mid-basics",
        "mid-wave",
        "mid-rotations",
        "mid-river",
        "mid-vision",
        "mid-ganks",
        "mid-turtle",
        "mid-lord",
        "mid-gold",
        "mid-exp",
        "mid-jungle",
        "mid-buff",
        "mid-early",
        "mid-matchup",
        "mid-tower",
        "mid-late",
        "mid-recall",
        "mid-map",
        "mid-mistakes",
        "mid-teamfights",
    ],
    "jungle": [
        "jungle-basics",
        "jungle-clear",
        "jungle-buffs",
        "jungle-retribution",
        "jungle-ganks",
        "jungle-path",
        "jungle-invade",
        "jungle-turtle",
        "jungle-lord",
        "jungle-gold",
        "jungle-mid",
        "jungle-exp",
        "jungle-roam",
        "jungle-early",
        "jungle-late",
        "jungle-recall",
        "jungle-map",
        "jungle-mistakes",
        "jungle-teamfights",
        "jungle-behind",
    ],
    "exp": [
        "exp-basics",
        "exp-wave",
        "exp-level",
        "exp-trade",
        "exp-tower",
        "exp-gank",
        "exp-turtle",
        "exp-lord",
        "exp-rotate",
        "exp-gold",
        "exp-mid",
        "exp-jungle",
        "exp-roam",
        "exp-early",
        "exp-late",
        "exp-recall",
        "exp-map",
        "exp-mistakes",
        "exp-teamfights",
        "exp-behind",
    ],
    "gold": [
        "gold-basics",
        "gold-wave",
        "gold-items",
        "gold-trade",
        "gold-tower",
        "gold-gank",
        "gold-turtle",
        "gold-lord",
        "gold-rotate",
        "gold-exp",
        "gold-mid",
        "gold-jungle",
        "gold-roam",
        "gold-early",
        "gold-late",
        "gold-recall",
        "gold-map",
        "gold-mistakes",
        "gold-teamfights",
        "gold-behind",
    ],
}


def cover_for(role: str, index: int) -> str:
    return f"/images/quiz/{role}-{(index % 4) + 1}.svg"


def _field(text: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+?)\s*$", text, re.M)
    if not match:
        raise ValueError(f"missing {label}")
    return match.group(1).strip()


def _split_copy(text: str) -> tuple[str, str]:
    clean = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+", clean, maxsplit=1)
    title = parts[0]
    body = parts[1] if len(parts) > 1 else ""
    if len(title) > 255:
        title = title[:252].rstrip() + "…"
        body = clean
    return title, body


def _score_band(cell: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", cell.strip())
    if not match:
        raise ValueError(f"bad score band: {cell}")
    return int(match.group(1)), int(match.group(2))


def parse_quiz_markdown(text: str, role: str, index: int) -> dict:
    slug = _field(text, "Slug").strip("`")
    title_ru = _field(text, "RU")
    # The first RU/EN pair is the title; description and questions repeat the labels.
    title_block, rest = text.split("## Описание", 1)
    title_ru = _field(title_block, "RU")
    title_en = _field(title_block, "EN")
    desc_block, rest = rest.split("## Итоги", 1)
    description_ru = _field(desc_block, "RU")
    description_en = _field(desc_block, "EN")
    table_block, questions_block = rest.split("## Вопросы", 1)

    results = []
    for line in table_block.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not re.match(r"\d", cells[0]):
            continue
        minimum, maximum = _score_band(cells[0])
        ru_title, ru_body = _split_copy(cells[1])
        en_title, en_body = _split_copy(cells[2])
        results.append(
            {
                "min_correct": minimum,
                "max_correct": maximum,
                "translations": {
                    "ru": {"title": ru_title, "body": ru_body},
                    "en": {"title": en_title, "body": en_body},
                },
            }
        )
    if len(results) < 1:
        raise ValueError(f"{slug}: no result bands")

    questions = []
    chunks = re.split(r"^###\s+\d+\s*$", questions_block, flags=re.M)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk or not chunk.startswith("RU:"):
            continue
        prompt_ru = _field(chunk, "RU")
        prompt_en = _field(chunk, "EN")
        explanation_ru = _field(chunk, "Пояснение RU")
        explanation_en = _field(chunk, "Explanation EN")
        options = []
        for raw in chunk.splitlines():
            mark = re.match(r"^- \[([ xX])\]\s+(.+)$", raw.strip())
            if not mark:
                continue
            ru_text, en_text = mark.group(2).split(" / ", 1)
            options.append(
                {
                    "is_correct": mark.group(1).lower() == "x",
                    "translations": {
                        "ru": {"text": ru_text.strip()},
                        "en": {"text": en_text.strip()},
                    },
                }
            )
        if len(options) < 2 or not any(option["is_correct"] for option in options):
            raise ValueError(f"{slug}: bad options in {prompt_ru[:40]}")
        for option in options:
            for lang in ("ru", "en"):
                if len(option["translations"][lang]["text"]) > 500:
                    raise ValueError(f"{slug}: option longer than 500")
        questions.append(
            {
                "image": None,
                "translations": {
                    "ru": {"prompt": prompt_ru, "explanation": explanation_ru},
                    "en": {"prompt": prompt_en, "explanation": explanation_en},
                },
                "options": options,
            }
        )
    if not questions:
        raise ValueError(f"{slug}: no questions")

    return {
        "slug": slug,
        "game": "mlbb",
        "role": role,
        "cover_image": cover_for(role, index),
        "status": "published",
        "translations": {
            "ru": {"title": title_ru, "description": description_ru},
            "en": {"title": title_en, "description": description_en},
        },
        "questions": questions,
        "results": results,
    }


def load_mlbb_folder(folder: Path) -> list[dict]:
    quizzes: list[dict] = []
    for role, slugs in ROLE_ORDER.items():
        for index, slug in enumerate(slugs):
            path = folder / f"{slug}.md"
            if not path.is_file():
                raise FileNotFoundError(path)
            quizzes.append(parse_quiz_markdown(path.read_text(encoding="utf-8"), role, index))
    slugs = [quiz["slug"] for quiz in quizzes]
    if len(slugs) != len(set(slugs)):
        raise ValueError("duplicate quiz slug")
    return quizzes
