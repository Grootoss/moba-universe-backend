"""Selectable MOBA games and ranks for profile cabinet."""

GAMES: list[dict[str, str]] = [
    {"slug": "mlbb", "name_ru": "Mobile Legends", "name_en": "Mobile Legends"},
    {"slug": "lol", "name_ru": "League of Legends", "name_en": "League of Legends"},
    {"slug": "wildrift", "name_ru": "Wild Rift", "name_en": "Wild Rift"},
    {"slug": "dota2", "name_ru": "Dota 2", "name_en": "Dota 2"},
    {"slug": "aov", "name_ru": "Arena of Valor", "name_en": "Arena of Valor"},
    {"slug": "hok", "name_ru": "Honor of Kings", "name_en": "Honor of Kings"},
    {"slug": "smite", "name_ru": "Smite", "name_en": "Smite"},
]

GAME_SLUGS: frozenset[str] = frozenset(g["slug"] for g in GAMES)

# Five lanes/roles per game, numbered 1–5 with logical labels.
ROLES: dict[str, list[dict[str, str | int]]] = {
    "mlbb": [
        {"slug": "1", "number": 1, "name_ru": "1 · Эксп", "name_en": "1 · Exp"},
        {"slug": "2", "number": 2, "name_ru": "2 · Лес", "name_en": "2 · Jungle"},
        {"slug": "3", "number": 3, "name_ru": "3 · Мид", "name_en": "3 · Mid"},
        {"slug": "4", "number": 4, "name_ru": "4 · Золото", "name_en": "4 · Gold"},
        {"slug": "5", "number": 5, "name_ru": "5 · Роум", "name_en": "5 · Roam"},
    ],
    "lol": [
        {"slug": "1", "number": 1, "name_ru": "1 · Топ", "name_en": "1 · Top"},
        {"slug": "2", "number": 2, "name_ru": "2 · Лес", "name_en": "2 · Jungle"},
        {"slug": "3", "number": 3, "name_ru": "3 · Мид", "name_en": "3 · Mid"},
        {"slug": "4", "number": 4, "name_ru": "4 · АДК", "name_en": "4 · ADC"},
        {"slug": "5", "number": 5, "name_ru": "5 · Поддержка", "name_en": "5 · Support"},
    ],
    "wildrift": [
        {"slug": "1", "number": 1, "name_ru": "1 · Топ", "name_en": "1 · Top"},
        {"slug": "2", "number": 2, "name_ru": "2 · Лес", "name_en": "2 · Jungle"},
        {"slug": "3", "number": 3, "name_ru": "3 · Мид", "name_en": "3 · Mid"},
        {"slug": "4", "number": 4, "name_ru": "4 · АДК", "name_en": "4 · ADC"},
        {"slug": "5", "number": 5, "name_ru": "5 · Поддержка", "name_en": "5 · Support"},
    ],
    "dota2": [
        {"slug": "1", "number": 1, "name_ru": "1 · Керри", "name_en": "1 · Carry"},
        {"slug": "2", "number": 2, "name_ru": "2 · Мид", "name_en": "2 · Mid"},
        {"slug": "3", "number": 3, "name_ru": "3 · Сложная", "name_en": "3 · Offlane"},
        {"slug": "4", "number": 4, "name_ru": "4 · Частичная поддержка", "name_en": "4 · Soft support"},
        {"slug": "5", "number": 5, "name_ru": "5 · Полная поддержка", "name_en": "5 · Hard support"},
    ],
    "aov": [
        {"slug": "1", "number": 1, "name_ru": "1 · Дарк Слейер", "name_en": "1 · Dark Slayer"},
        {"slug": "2", "number": 2, "name_ru": "2 · Лес", "name_en": "2 · Jungle"},
        {"slug": "3", "number": 3, "name_ru": "3 · Мид", "name_en": "3 · Mid"},
        {"slug": "4", "number": 4, "name_ru": "4 · Эбиссл", "name_en": "4 · Abyssal"},
        {"slug": "5", "number": 5, "name_ru": "5 · Роум", "name_en": "5 · Roam"},
    ],
    "hok": [
        {"slug": "1", "number": 1, "name_ru": "1 · Клэш", "name_en": "1 · Clash"},
        {"slug": "2", "number": 2, "name_ru": "2 · Лес", "name_en": "2 · Jungle"},
        {"slug": "3", "number": 3, "name_ru": "3 · Мид", "name_en": "3 · Mid"},
        {"slug": "4", "number": 4, "name_ru": "4 · Фарм", "name_en": "4 · Farm"},
        {"slug": "5", "number": 5, "name_ru": "5 · Роум", "name_en": "5 · Roam"},
    ],
    "smite": [
        {"slug": "1", "number": 1, "name_ru": "1 · Соло", "name_en": "1 · Solo"},
        {"slug": "2", "number": 2, "name_ru": "2 · Лес", "name_en": "2 · Jungle"},
        {"slug": "3", "number": 3, "name_ru": "3 · Мид", "name_en": "3 · Mid"},
        {"slug": "4", "number": 4, "name_ru": "4 · Керри", "name_en": "4 · Carry"},
        {"slug": "5", "number": 5, "name_ru": "5 · Поддержка", "name_en": "5 · Support"},
    ],
}

ROLE_SLUGS: dict[str, frozenset[str]] = {
    game: frozenset(str(r["slug"]) for r in items) for game, items in ROLES.items()
}

RANKS: dict[str, list[str]] = {
    "mlbb": [
        "Warrior",
        "Elite",
        "Master",
        "Grandmaster",
        "Epic",
        "Legend",
        "Mythic",
        "Mythic 1-24 stars",
        "Mythical Honor",
        "Mythical Glory",
        "Mythical Immortal",
    ],
    "lol": [
        "Iron",
        "Bronze",
        "Silver",
        "Gold",
        "Platinum",
        "Emerald",
        "Diamond",
        "Master",
        "Grandmaster",
        "Challenger",
    ],
    "wildrift": [
        "Iron",
        "Bronze",
        "Silver",
        "Gold",
        "Platinum",
        "Emerald",
        "Diamond",
        "Master",
        "Grandmaster",
        "Challenger",
        "Sovereign",
    ],
    "dota2": [
        "Herald",
        "Guardian",
        "Crusader",
        "Archon",
        "Legend",
        "Ancient",
        "Divine",
        "Immortal",
        "Immortal Top 1000",
        "Immortal Top 100",
    ],
    "aov": [
        "Bronze",
        "Silver",
        "Gold",
        "Platinum",
        "Diamond",
        "Master",
        "Conqueror",
        "Grand Conqueror",
        "Legendary Conqueror",
        "Glorious Conqueror",
    ],
    "hok": [
        "Bronze",
        "Silver",
        "Gold",
        "Platinum",
        "Diamond",
        "Starlight",
        "King",
        "High King",
        "Glory",
        "Mythic",
    ],
    "smite": [
        "Bronze",
        "Silver",
        "Gold",
        "Platinum",
        "Diamond",
        "Masters",
        "Grandmaster",
    ],
}
