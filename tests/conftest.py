"""Shared fixtures: PostgreSQL (schema pytest) + FastAPI TestClient."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.models import (
    Article,
    ArticleStatus,
    ArticleTranslation,
    Category,
    User,
    UserRole,
)
from app.security import hash_password
from main import app

get_settings.cache_clear()

TEST_SCHEMA = "pytest"


def _test_database_url() -> str:
    """Prefer TEST_DATABASE_URL, else the same Postgres as the app (DATABASE_URL)."""
    return (
        os.getenv("TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL_TEST")
        or get_settings().database_url
    )


@pytest.fixture()
def db_session():
    url = _test_database_url()
    if not url.startswith("postgresql"):
        raise RuntimeError(
            "Tests require PostgreSQL. Set TEST_DATABASE_URL or DATABASE_URL "
            "to a postgresql+psycopg://... connection string."
        )

    engine = create_engine(url, pool_pre_ping=True)

    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE'))
        conn.execute(text(f'CREATE SCHEMA "{TEST_SCHEMA}"'))

    @event.listens_for(engine, "connect")
    def set_search_path(dbapi_connection, _connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{TEST_SCHEMA}"')
        cursor.close()

    # Apply search_path on the already-open pool connection used next
    with engine.begin() as conn:
        conn.execute(text(f'SET search_path TO "{TEST_SCHEMA}"'))

    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE'))
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db_session):
    user = User(
        email="admin@mobauniverse.com",
        username="admin",
        password_hash=hash_password("adminpass"),
        role=UserRole.admin.value,
        profile_edit_unlocked=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def regular_user(db_session):
    user = User(
        email="player@example.com",
        username="player",
        password_hash=hash_password("player1"),
        role=UserRole.user.value,
        profile_edit_unlocked=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def category(db_session):
    cat = Category(slug="guides", name_ru="Гайды", name_en="Guides")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture()
def published_article(db_session, admin_user, category):
    article = Article(
        slug="mythic-guide",
        category_id=category.id,
        author_id=admin_user.id,
        status=ArticleStatus.published.value,
    )
    article.translations.append(
        ArticleTranslation(
            lang="ru",
            title="Как апнуть миф",
            excerpt="Кратко",
            content="<p>Текст</p>",
        )
    )
    article.translations.append(
        ArticleTranslation(
            lang="en",
            title="How to reach Mythic",
            excerpt="Short",
            content="<p>Text</p>",
        )
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    return article


@pytest.fixture()
def draft_article(db_session, admin_user, category):
    article = Article(
        slug="draft-only",
        category_id=category.id,
        author_id=admin_user.id,
        status=ArticleStatus.draft.value,
    )
    article.translations.append(
        ArticleTranslation(lang="ru", title="Черновик", excerpt="", content="<p>x</p>")
    )
    article.translations.append(
        ArticleTranslation(lang="en", title="Draft", excerpt="", content="<p>x</p>")
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    return article


def auth_header(client: TestClient, email: str, password: str) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
