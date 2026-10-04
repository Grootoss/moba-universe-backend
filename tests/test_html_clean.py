from app.html_clean import clean_article_html


def test_clean_article_html_drops_active_markup():
    raw = (
        '<p onclick="steal()">ok</p>'
        '<a href="javascript:alert(1)">x</a>'
        "<script>alert(1)</script>"
        "<iframe src=\"https://evil.test\"></iframe>"
    )
    cleaned = clean_article_html(raw)
    assert "<script" not in cleaned.lower()
    assert "<iframe" not in cleaned.lower()
    assert "onclick" not in cleaned.lower()
    assert "javascript:" not in cleaned.lower()
    assert "ok" in cleaned
    assert "https://evil.test" not in cleaned
