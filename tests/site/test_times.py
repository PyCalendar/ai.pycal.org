"""Times are shown like on GitHub: how long ago, the exact time on hover, local in the browser."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from django.template import Context, Template
from django.utils import timezone as django_timezone

from ai_pycal.templatetags.times import ago

NOW = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("before", "text"),
    [
        (timedelta(seconds=10), "just now"),
        (timedelta(minutes=1), "1 minute ago"),
        (timedelta(minutes=59), "59 minutes ago"),
        (timedelta(hours=1), "1 hour ago"),
        (timedelta(hours=23), "23 hours ago"),
        (timedelta(hours=30), "yesterday"),
        (timedelta(days=29), "29 days ago"),
        (timedelta(days=30), "on 2026-10-13"),
    ],
)
def test_how_long_ago(before, text):
    assert ago(NOW - before, NOW) == text


def test_the_tag_shows_utc_on_hover_for_any_time_zone(monkeypatch):
    monkeypatch.setattr(django_timezone, "now", lambda: NOW)
    berlin = timezone(timedelta(hours=1))
    html = Template("{% load times %}{% when value %}").render(
        Context({"value": datetime(2026, 11, 12, 14, 0, tzinfo=berlin)})
    )
    assert html == (
        '<time class="when" datetime="2026-11-12T13:00:00Z" title="2026-11-12 13:00 UTC">'
        "2 hours ago</time>"
    )


def test_no_time_is_empty():
    assert Template("{% load times %}{% when value %}").render(Context({"value": None})) == ""


def test_no_page_formats_times_itself():
    from pathlib import Path

    for template in (Path(__file__).parents[2] / "ai_pycal" / "templates").rglob("*.html"):
        text = template.read_text()
        assert "|date:" not in text, template
        assert "<time " not in text or "times.py" in text, template
