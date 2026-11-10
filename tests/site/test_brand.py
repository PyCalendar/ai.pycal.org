"""The colors and the icon of the site can be changed."""

import pytest
from django.core.checks import run_checks

from ai_pycal import errors
from ai_pycal.theme import LIGHT, Theme

pytestmark = pytest.mark.django_db


def test_the_pycal_colors_are_the_default(client):
    page = client.get("/").content.decode()
    assert "--brand: #3b79aa;" in page
    assert "--accent: #ffd43b;" in page
    assert "prefers-color-scheme: dark" in page


def test_the_colors_can_be_changed(client, settings):
    settings.THEME = Theme.from_environment(
        {"COLOR_PRIMARY": "#112233", "COLOR_DARK_SURFACE": "#000"}
    )
    page = client.get("/").content.decode()
    assert "--primary: #112233;" in page
    assert "--surface: #000;" in page


@pytest.mark.parametrize(
    ("environ", "error"),
    [
        ({"COLOR_PRIMARY": "blue"}, errors.InvalidColor),
        ({"COLOR_PRIMARY": "#12345"}, errors.InvalidColor),
        ({"COLOR_PRIMRY": "#123456"}, errors.UnknownColor),
        ({"COLOR_DARK_NOPE": "#123456"}, errors.UnknownColor),
    ],
)
def test_wrong_colors(environ, error):
    with pytest.raises(error):
        Theme.from_environment(environ)


def test_every_color_is_documented():
    from pathlib import Path

    text = (Path(__file__).parents[2] / "docs" / "how-to" / "brand.rst").read_text()
    for name in LIGHT:
        assert f"COLOR_{name.upper()}" in text, name


def test_extra_css(client, settings):
    settings.EXTRA_CSS_URL = "https://example.org/brand.css"
    assert b'href="https://example.org/brand.css"' in client.get("/").content


def test_the_default_favicon(client):
    response = client.get("/favicon.ico")
    assert response["Content-Type"] == "image/png"
    assert b"".join(response.streaming_content)[:4] == b"\x89PNG"


def test_an_own_favicon(client, settings, tmp_path):
    icon = tmp_path / "icon.svg"
    icon.write_text("<svg/>")
    settings.FAVICON_FILE = str(icon)
    response = client.get("/favicon.ico")
    assert response["Content-Type"] == "image/svg+xml"
    assert b"".join(response.streaming_content) == b"<svg/>"
    assert not [m for m in run_checks() if m.id.startswith("ai_pycal.E")]


@pytest.mark.parametrize(
    ("name", "check"), [("missing.png", "ai_pycal.E001"), ("icon.gif", "ai_pycal.E002")]
)
def test_a_wrong_favicon_stops_the_start(settings, tmp_path, name, check):
    (tmp_path / "icon.gif").write_bytes(b"GIF")
    settings.FAVICON_FILE = str(tmp_path / name)
    assert check in [message.id for message in run_checks()]
