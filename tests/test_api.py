from tests.conftest import auth_header
from app.models import Category


def test_register_and_login(client):
    payload = {
        "email": "newuser@example.com",
        "username": "NewUser",
        "password": "secret12",
        "password_confirm": "secret12",
        "privacy_consent": True,
    }
    reg = client.post("/api/auth/register", json=payload)
    assert reg.status_code == 201
    body = reg.json()
    assert "access_token" in body
    assert "refresh_token" in body

    login = client.post(
        "/api/auth/login",
        json={"email": "newuser@example.com", "password": "secret12"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.status_code == 200
    data = me.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert data["role"] == "user"


def test_login_invalid_password(client, regular_user):
    res = client.post(
        "/api/auth/login",
        json={"email": regular_user.email, "password": "wrongpass"},
    )
    assert res.status_code == 401


def test_list_articles_published_only(client, published_article, draft_article):
    res = client.get("/api/evergreen/articles")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    slugs = {a["slug"] for a in items}
    assert "mythic-guide" in slugs
    assert "draft-only" not in slugs


def test_get_article_by_slug(client, published_article):
    res = client.get("/api/evergreen/articles/mythic-guide")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == "mythic-guide"
    assert "ru" in data["translations"]
    assert data["translations"]["ru"]["title"] == "Как апнуть миф"
    assert "mlbb_example" in data["translations"]["ru"]
    assert data.get("created_at")
    assert data.get("updated_at")


def test_list_categories_public(client, category):
    res = client.get("/api/evergreen/categories")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(c["slug"] == category.slug for c in data)


def test_filter_articles_by_category(client, published_article, category, admin_user, db_session):
    other = Category(slug="empty-cat", name_ru="Пусто", name_en="Empty")
    db_session.add(other)
    db_session.commit()

    res = client.get(f"/api/evergreen/articles?paginated=true&category={category.slug}")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(i["slug"] == "mythic-guide" for i in body["items"])

    res_empty = client.get("/api/evergreen/articles?paginated=true&category=empty-cat")
    assert res_empty.status_code == 200
    assert res_empty.json()["total"] == 0


def test_admin_mlbb_example_roundtrip(client, admin_user, category):
    headers = auth_header(client, admin_user.email, "adminpass")
    res = client.post(
        "/api/admin/articles",
        headers=headers,
        json={
            "slug": "mlbb-block-test",
            "category_slug": category.slug,
            "status": "published",
            "translations": {
                "ru": {
                    "title": "RU",
                    "excerpt": "",
                    "content": "<p>ru</p>",
                    "mlbb_example": "<p>mlbb ru</p>",
                },
                "en": {
                    "title": "EN",
                    "excerpt": "",
                    "content": "<p>en</p>",
                    "mlbb_example": "<p>mlbb en</p>",
                },
            },
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["mlbb_example_ru"] == "<p>mlbb ru</p>"
    assert data["mlbb_example_en"] == "<p>mlbb en</p>"

    public = client.get("/api/evergreen/articles/mlbb-block-test")
    assert public.status_code == 200
    tr = public.json()["translations"]
    assert tr["ru"]["mlbb_example"] == "<p>mlbb ru</p>"
    assert tr["en"]["mlbb_example"] == "<p>mlbb en</p>"


def test_get_article_missing_slug(client):
    res = client.get("/api/evergreen/articles/no-such-slug")
    assert res.status_code == 404


def test_crud_requires_auth(client):
    res = client.post(
        "/api/admin/articles",
        json={
            "slug": "x",
            "status": "published",
            "translations": {
                "ru": {"title": "t", "excerpt": "", "content": "c"},
                "en": {"title": "t", "excerpt": "", "content": "c"},
            },
        },
    )
    assert res.status_code == 401


def test_crud_forbidden_for_user(client, regular_user):
    headers = auth_header(client, regular_user.email, "player1")
    res = client.post(
        "/api/admin/articles",
        headers=headers,
        json={
            "slug": "user-article",
            "status": "published",
            "translations": {
                "ru": {"title": "t", "excerpt": "", "content": "c"},
                "en": {"title": "t", "excerpt": "", "content": "c"},
            },
        },
    )
    assert res.status_code == 403


def test_create_article_as_admin(client, admin_user, category):
    headers = auth_header(client, admin_user.email, "adminpass")
    res = client.post(
        "/api/admin/articles",
        headers=headers,
        json={
            "slug": "admin-created",
            "category_slug": category.slug,
            "status": "published",
            "cover_image": "https://example.com/c.jpg",
            "translations": {
                "ru": {"title": "Заголовок", "excerpt": "e", "content": "<p>ru</p>"},
                "en": {"title": "Title", "excerpt": "e", "content": "<p>en</p>"},
            },
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["slug"] == "admin-created"
    assert data["status"] == "published"
    assert data["title_ru"] == "Заголовок"

    public = client.get("/api/evergreen/articles/admin-created")
    assert public.status_code == 200
    assert public.json()["cover_image"] == "https://example.com/c.jpg"


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_robots_txt(client):
    res = client.get("/robots.txt")
    assert res.status_code == 200
    assert "Sitemap:" in res.text
    assert "Allow: /ru/evergreen" in res.text
    assert "Allow: /en/evergreen" in res.text
    assert "Disallow: /admin" in res.text
    assert "Disallow: /admin/" in res.text


def test_sitemap_includes_published_article(client, published_article):
    res = client.get("/sitemap.xml")
    assert res.status_code == 200
    assert "application/xml" in res.headers["content-type"]
    assert "/ru/evergreen/mythic-guide" in res.text
    assert "/en/evergreen/mythic-guide" in res.text
    assert "/ru/evergreen" in res.text
    assert "/en/evergreen" in res.text
