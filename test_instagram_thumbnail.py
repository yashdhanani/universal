import pytest
from backend.platforms import instagram as ig


def test_thumbnail_pass_through(monkeypatch):
    """If source has `thumbnail`, it becomes `thumbnail_url`."""
    def fake_analyze_platform(url, platform, patterns):
        return {"thumbnail": "https://cdn.example.com/tn.jpg"}

    monkeypatch.setattr(ig, "analyze_platform", fake_analyze_platform)
    out = ig.analyze("https://instagram.com/p/ABC123/?utm=foo")
    assert out["thumbnail_url"] == "https://cdn.example.com/tn.jpg"


def test_thumbnail_from_display_url(monkeypatch):
    """If source has `display_url`, use it for `thumbnail_url`."""
    def fake_analyze_platform(url, platform, patterns):
        return {"display_url": "https://cdn.example.com/display.jpg"}

    monkeypatch.setattr(ig, "analyze_platform", fake_analyze_platform)
    out = ig.analyze("https://instagram.com/reel/ABC123/")
    assert out["thumbnail_url"] == "https://cdn.example.com/display.jpg"


def test_thumbnail_from_display_resources(monkeypatch):
    """If source has `display_resources`, use the last item's `src`."""
    def fake_analyze_platform(url, platform, patterns):
        return {"display_resources": [{"src": "https://cdn.example.com/1.jpg"}, {"src": "https://cdn.example.com/2.jpg"}]}

    monkeypatch.setattr(ig, "analyze_platform", fake_analyze_platform)
    out = ig.analyze("https://instagr.am/p/XYZ/")
    assert out["thumbnail_url"] == "https://cdn.example.com/2.jpg"


def test_thumbnail_fallback_default(monkeypatch):
    """If no thumbnail-like fields exist, fallback to default icon."""
    def fake_analyze_platform(url, platform, patterns):
        return {}

    monkeypatch.setattr(ig, "analyze_platform", fake_analyze_platform)
    out = ig.analyze("https://instagram.com/someuser")
    assert out["thumbnail_url"] == "/static/og-default.svg"


def test_none_info_passthrough(monkeypatch):
    """If analyze_platform returns None (e.g., non-fetchable URL), propagate None."""
    def fake_analyze_platform(url, platform, patterns):
        return None

    monkeypatch.setattr(ig, "analyze_platform", fake_analyze_platform)
    out = ig.analyze("https://instagram.com/p/ABC/")
    assert out is None