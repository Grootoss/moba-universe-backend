from app.media import derive_cover_thumb


def test_explicit_thumb_is_kept():
    assert (
        derive_cover_thumb("/images/article-9.png", "/images/thumbs/hilda-10.jpg")
        == "/images/thumbs/hilda-10.jpg"
    )


def test_full_size_thumb_is_rewritten():
    assert (
        derive_cover_thumb("/images/article-13.png", "/images/article-13.png")
        == "/images/thumbs/article-13.jpg"
    )


def test_cover_alone_derives_thumb():
    assert derive_cover_thumb("/images/roles-03.png", None) == "/images/thumbs/roles-03.jpg"


def test_remote_thumb_is_kept():
    assert derive_cover_thumb(None, "https://cdn.example/a.jpg") == "https://cdn.example/a.jpg"


def test_empty_is_none():
    assert derive_cover_thumb(None, None) is None
    assert derive_cover_thumb("  ", "") is None
