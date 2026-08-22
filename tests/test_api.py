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
    assert data["username"] == "NewUser"
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
    assert "/ru</loc>" in res.text
    assert "/en</loc>" in res.text


def _publish_profile(db_session, user, nickname, games=None, contacts=None):
    from app.models import UserGameRank, UserProfile
    from app.models import ModerationStatus

    profile = UserProfile(
        user_id=user.id,
        nickname=nickname,
        bio="bio",
        moderation_status=ModerationStatus.approved.value,
        is_public=True,
        social_links=contacts or [],
    )
    db_session.add(profile)
    db_session.flush()
    for i, g in enumerate(games or []):
        db_session.add(
            UserGameRank(
                profile_id=profile.id,
                game=g["game"],
                rank=g["rank"],
                roles=g.get("roles") or [],
                sort_order=i,
            )
        )
    db_session.commit()
    db_session.refresh(profile)
    return profile


def test_users_search_by_name_game_role(client, db_session, regular_user):
    from app.models import User
    from app.security import hash_password

    other = User(
        email="midlaner@example.com",
        username="midlaner",
        password_hash=hash_password("secret12"),
        role="user",
        profile_edit_unlocked=True,
    )
    db_session.add(other)
    db_session.commit()

    _publish_profile(
        db_session,
        regular_user,
        "GoldCarry",
        games=[{"game": "mlbb", "rank": "Mythic", "roles": ["4", "5"]}],
    )
    _publish_profile(
        db_session,
        other,
        "MidOnly",
        games=[{"game": "lol", "rank": "Gold", "roles": ["3"]}],
    )

    by_name = client.get("/api/users?q=gold")
    assert by_name.status_code == 200
    nicks = {u["nickname"] for u in by_name.json()}
    assert "GoldCarry" in nicks
    assert "MidOnly" not in nicks
    assert by_name.json()[0]["games"][0]["rank"] == "Mythic"

    by_username = client.get("/api/users?q=MID")
    assert {u["nickname"] for u in by_username.json()} == {"MidOnly"}

    by_partial = client.get("/api/users?q=Carry")
    assert {u["nickname"] for u in by_partial.json()} == {"GoldCarry"}


def test_contact_request_flow(client, db_session, regular_user):
    from app.models import User
    from app.security import hash_password
    from tests.conftest import auth_header

    other = User(
        email="target@example.com",
        username="targetu",
        password_hash=hash_password("secret12"),
        role="user",
        profile_edit_unlocked=True,
    )
    db_session.add(other)
    db_session.commit()
    _publish_profile(
        db_session,
        other,
        "TargetNick",
        contacts=[
            {"label": "Telegram", "url": "https://t.me/secret", "is_public": False},
            {"label": "Discord", "url": "https://discord.gg/public", "is_public": True},
        ],
    )

    public = client.get(f"/api/users/{other.id}")
    assert public.status_code == 200
    labels = {c["label"] for c in public.json()["contacts"]}
    assert "Discord" in labels
    assert "Telegram" not in labels

    headers = auth_header(client, regular_user.email, "player1")
    req = client.post(f"/api/users/{other.id}/contact-request", headers=headers)
    assert req.status_code == 200, req.text
    assert req.json()["status"] == "pending"
    assert req.json()["contacts"] is None

    other_headers = auth_header(client, other.email, "secret12")
    inbox = client.get("/api/me/contacts", headers=other_headers)
    assert inbox.status_code == 200
    assert len(inbox.json()["incoming"]) == 1
    request_id = inbox.json()["incoming"][0]["request_id"]

    accepted = client.post(f"/api/me/contacts/{request_id}/accept", headers=other_headers)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    mine = client.get("/api/me/contacts", headers=headers)
    assert mine.status_code == 200
    outgoing = mine.json()["outgoing"]
    assert outgoing[0]["status"] == "accepted"
    urls = {c["url"] for c in outgoing[0]["contacts"]}
    assert "https://t.me/secret" in urls


def test_profile_options_include_roles(client):
    res = client.get("/api/profile/options")
    assert res.status_code == 200
    data = res.json()
    assert "mlbb" in data["roles"]
    assert len(data["roles"]["mlbb"]) == 5
    assert data["roles"]["mlbb"][0]["slug"] == "1"

