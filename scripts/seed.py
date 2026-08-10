"""Seed DB: admin, Rootoss profile, categories (no articles)."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python scripts/seed.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import (
    Category,
    GameType,
    ModerationStatus,
    User,
    UserGameRank,
    UserProfile,
    UserRole,
)
from app.security import hash_password
from content.seed_articles import CATEGORIES

ADMIN_EMAIL = "admin@mobauniverse.com"
ADMIN_USERNAME = "admin"

ROOTOSS = {
    "email": "rootoss@mobauniverse.com",
    "username": "rootoss",
    "password": "player123",
    "nickname": "Rootoss",
    "bio": (
        "Привет! Я играю в MOBA уже несколько сезонов и люблю разбирать реплеи.\n\n"
        "За это время апнул высокий ранг."
    ),
    "telegram_url": None,
    "social_links": {},
    "games": [
        {"game": GameType.mlbb.value, "rank": "Mythic 18 stars", "sort_order": 0},
    ],
}


def _upsert_profile(db, demo: dict) -> User:
    # Migrate old seed email player1 → rootoss
    legacy = db.scalar(select(User).where(User.email == "player1@mobauniverse.com"))
    if legacy and demo["email"] != "player1@mobauniverse.com":
        existing_new = db.scalar(select(User).where(User.email == demo["email"]))
        if not existing_new:
            legacy.email = demo["email"]
            legacy.username = demo["username"]
            db.flush()

    user = db.scalar(select(User).where(User.email == demo["email"]))
    if not user:
        user = User(
            email=demo["email"],
            username=demo["username"],
            password_hash=hash_password(demo["password"]),
            role=UserRole.user.value,
            profile_edit_unlocked=True,
        )
        db.add(user)
        db.flush()
    else:
        user.username = demo["username"]
        user.profile_edit_unlocked = True

    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if not profile:
        profile = UserProfile(
            user_id=user.id,
            nickname=demo["nickname"],
            bio=demo["bio"],
            telegram_url=demo.get("telegram_url"),
            social_links=demo.get("social_links") or {},
            moderation_status=ModerationStatus.approved.value,
            moderation_note="",
            is_public=True,
        )
        db.add(profile)
        db.flush()
    else:
        profile.nickname = demo["nickname"]
        profile.bio = demo["bio"]
        profile.telegram_url = demo.get("telegram_url")
        profile.social_links = demo.get("social_links") or {}
        profile.moderation_status = ModerationStatus.approved.value
        profile.moderation_note = ""
        profile.is_public = True

    profile.game_ranks.clear()
    db.flush()
    for g in demo["games"]:
        db.add(
            UserGameRank(
                profile_id=profile.id,
                game=g["game"],
                rank=g["rank"],
                sort_order=g["sort_order"],
            )
        )
    print(f"Upserted profile /user/{user.id} ({demo['nickname']})")
    return user


def seed() -> None:
    db = SessionLocal()
    try:
        # /user/1 — Rootoss (create first on empty DB)
        _upsert_profile(db, ROOTOSS)

        # Remove old demo /user/2 if present
        player2 = db.scalar(select(User).where(User.email == "player2@mobauniverse.com"))
        if player2:
            profile2 = db.scalar(select(UserProfile).where(UserProfile.user_id == player2.id))
            if profile2:
                db.delete(profile2)
                db.flush()
            db.delete(player2)
            db.flush()
            print("Deleted demo user player2")

        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if not admin:
            admin_password = (get_settings().admin_password or "").strip()
            if not admin_password:
                raise SystemExit(
                    "Admin does not exist. Set ADMIN_PASSWORD in .env "
                    f"to create {ADMIN_EMAIL}."
                )
            admin = User(
                email=ADMIN_EMAIL,
                username=ADMIN_USERNAME,
                password_hash=hash_password(admin_password),
                role=UserRole.admin.value,
                profile_edit_unlocked=True,
            )
            db.add(admin)
            db.flush()
            print(f"Created admin {ADMIN_EMAIL}")
        else:
            admin.username = ADMIN_USERNAME
            admin.profile_edit_unlocked = True
            print(f"Admin already exists: {ADMIN_EMAIL}")

        for c in CATEGORIES:
            existing = db.scalar(select(Category).where(Category.slug == c["slug"]))
            if existing:
                print(f"Category exists: {c['slug']}")
            else:
                cat = Category(slug=c["slug"], name_ru=c["name_ru"], name_en=c["name_en"])
                db.add(cat)
                db.flush()
                print(f"Category: {c['slug']}")

        db.commit()
        print("Seed OK")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
