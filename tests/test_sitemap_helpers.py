from datetime import date, datetime, timezone

from app.routers.seo import _hub_entries, _lastmod, _render, _xml


def test_lastmod_accepts_datetime_and_date():
    assert _lastmod(datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)) == "2026-08-14"
    assert _lastmod(date(2026, 8, 10)) == "2026-08-10"
    assert _lastmod(None) is None


def test_hubs_omit_lastmod_and_x_default_is_russian():
    xml = _render(_hub_entries("https://mobauniverse.com"))
    assert "<lastmod>" not in xml
    assert 'hreflang="x-default" href="https://mobauniverse.com/ru"' in xml
    assert "/ru/evergreen" in xml
    assert "/en/privacy" in xml


def test_xml_escapes_quotes_in_urls():
    assert "&quot;" in _xml('https://example.com/a"b')
